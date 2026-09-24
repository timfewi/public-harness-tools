#!/usr/bin/env python3
"""Export deterministic, allowlisted public mirrors of private tool repositories.

Only Git-tracked files at ``HEAD`` are considered: the source working tree is
never read directly, so uncommitted or ignored state cannot leak. Text files
pass through the reviewed replacement policy in ``public_tool_rules.json`` and
the finished mirror is scanned for forbidden names, credentials, operator paths
and unexpected email addresses. A mirror is written only when every check
passes.

Usage:

    export_public_tools.py --source /path/to/repo --name repo-name
    export_public_tools.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "tools"
RULES_PATH = ROOT / "scripts" / "public_tool_rules.json"

MANIFEST_SCHEMA = "public-tool-mirror.v1"
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
EMAIL_RE = re.compile(
    rb"[A-Za-z0-9][A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]*"
    rb"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    rb"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)

EXCLUDED_DIRECTORIES = {
    ".astro",
    ".direnv",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".wrangler",
    "__pycache__",
    "dist",
    "node_modules",
    "result",
    "target",
    "venv",
}
EXCLUDED_NAMES = {
    ".DS_Store",
    ".env",
    "credentials",
    "credentials.json",
    "secrets.json",
}
EXCLUDED_SUFFIXES = {
    ".bak",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pyc",
    ".pyo",
    ".swp",
    ".tmp",
}
MAX_FILE_BYTES = 2 * 1024 * 1024


def credential_rules() -> dict[str, bytes]:
    # Split literals keep this scanner from matching its own source.
    return {
        "private-key marker": b"BEGIN " + b"(?:RSA |EC |OPENSSH )?PRIVATE KEY",
        "GitHub token": b"gh" + b"[pousr]_[A-Za-z0-9_]{20,}",
        "AWS access-key identifier": b"AK" + b"IA[0-9A-Z]{16}",
        "OpenAI-style secret key": b"sk"
        + b"-(?:[A-Za-z0-9]{32,}|(?:proj|svcacct)-[A-Za-z0-9_-]{20,})",
        "Slack token": b"xox" + b"[abopr]-[A-Za-z0-9-]{10,}",
    }


def load_rules(path: Path = RULES_PATH) -> dict:
    rules = json.loads(path.read_text(encoding="utf-8"))
    if rules.get("version") != 1:
        raise ValueError(f"unsupported rules version in {path}")
    for entry in rules.get("replacements", []):
        re.compile(entry["pattern"])
    for entry in rules.get("forbidden", []):
        re.compile(entry["pattern"])
    return rules


def run_git(source: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *arguments],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout


def repository_name(source: Path, fallback: str) -> str:
    try:
        url = run_git(source, "config", "--get", "remote.origin.url")
    except RuntimeError:
        return fallback
    match = re.search(
        rb"(?:github\.com[:/])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?\s*\Z",
        url.strip(),
    )
    return match.group(1).decode() if match else fallback


def is_excluded(relative: str) -> bool:
    parts = Path(relative).parts
    if any(part in EXCLUDED_DIRECTORIES for part in parts):
        return True
    name = parts[-1]
    return (
        name in EXCLUDED_NAMES
        or name.startswith(".env.")
        or Path(name).suffix in EXCLUDED_SUFFIXES
    )


def tracked_files(source: Path) -> dict[str, bytes]:
    """Return the Git-tracked files at HEAD, refusing non-regular entries."""
    archive = run_git(source, "archive", "--format=tar", "HEAD")
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(
                    f"refusing non-regular tracked entry: {member.name}"
                )
            if is_excluded(member.name):
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read tracked entry: {member.name}")
            files[member.name] = extracted.read()
    return files


def sanitize(data: bytes, replacements: list[dict]) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for entry in replacements:
        text = re.sub(entry["pattern"], entry["replacement"], text)
    return text.encode("utf-8")


def scan_tree(root: Path, rules: dict) -> list[tuple[str, str, int | None]]:
    findings: list[tuple[str, str, int | None]] = []
    forbidden = [
        (re.compile(entry["pattern"].encode(), re.IGNORECASE), entry["reason"])
        for entry in rules.get("forbidden", [])
    ]
    credentials = [
        (re.compile(pattern), label) for label, pattern in credential_rules().items()
    ]
    allowed_emails = tuple(rules.get("allowed_emails", []))
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            findings.append((relative, "file exceeds the mirror size limit", None))
        for pattern, reason in forbidden:
            for match in pattern.finditer(raw):
                line = raw.count(b"\n", 0, match.start()) + 1
                findings.append((relative, f"forbidden content: {reason}", line))
        for pattern, label in credentials:
            for match in pattern.finditer(raw):
                line = raw.count(b"\n", 0, match.start()) + 1
                findings.append((relative, f"credential pattern: {label}", line))
        for match in EMAIL_RE.finditer(raw):
            domain = match.group(0).rsplit(b"@", 1)[1].decode("ascii", "replace")
            if not domain.lower().endswith(allowed_emails):
                line = raw.count(b"\n", 0, match.start()) + 1
                findings.append((relative, f"unexpected email domain: {domain}", line))
    return findings


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(f"{file_digest}  {relative}\n".encode())
    return digest.hexdigest()


def write_mirror(source: Path, name: str, dest: Path, rules: dict) -> tuple[dict, Path]:
    if not NAME_RE.match(name):
        raise ValueError(f"invalid mirror name: {name!r}")
    revision = run_git(source, "rev-parse", "HEAD").decode().strip()
    files = tracked_files(source)
    if not files:
        raise ValueError(f"source has no tracked files: {source}")

    dest.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}.", dir=dest))
    try:
        for relative in sorted(files):
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(sanitize(files[relative], rules["replacements"]))
        findings = scan_tree(staging, rules)
        if findings:
            report = "\n".join(
                f"{path}:{line}: {label}" if line else f"{path}: {label}"
                for path, label, line in findings
            )
            raise ValueError(f"mirror verification failed:\n{report}")
        return {
            "name": name,
            "upstream": repository_name(source, name),
            "revision": revision,
            "files": len(files),
            "digest": f"sha256:{tree_digest(staging)}",
        }, staging
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def install_mirror(staging_parent: Path, name: str, dest: Path, force: bool) -> None:
    target = dest / name
    if target.exists() and not force:
        shutil.rmtree(staging_parent, ignore_errors=True)
        raise FileExistsError(f"mirror already exists: {target} (use --force)")
    if target.exists():
        shutil.rmtree(target)
    try:
        os.replace(staging_parent, target)
    except BaseException:
        shutil.rmtree(staging_parent, ignore_errors=True)
        raise


def refresh_manifest(dest: Path, entry: dict | None) -> None:
    manifest_path = dest / "manifest.json"
    existing: dict[str, dict] = {}
    if manifest_path.is_file():
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        if document.get("schema") != MANIFEST_SCHEMA:
            raise ValueError(f"unsupported manifest schema in {manifest_path}")
        existing = {tool["name"]: tool for tool in document["tools"]}
    if entry is not None:
        existing[entry["name"]] = entry

    tools = []
    for directory in sorted(dest.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        previous = existing.get(directory.name)
        tools.append(
            {
                "name": directory.name,
                "upstream": (previous or {}).get("upstream", directory.name),
                "revision": (previous or {}).get("revision", "unknown"),
                "files": sum(1 for path in directory.rglob("*") if path.is_file()),
                "digest": f"sha256:{tree_digest(directory)}",
            }
        )
    manifest_path.write_text(
        json.dumps(
            {"schema": MANIFEST_SCHEMA, "tools": tools},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def verify_mirrors(dest: Path, rules: dict) -> list[str]:
    manifest_path = dest / "manifest.json"
    if not manifest_path.is_file():
        return [f"missing manifest: {manifest_path}"]
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema") != MANIFEST_SCHEMA:
        return [f"unsupported manifest schema in {manifest_path}"]
    problems: list[str] = []
    entries = {tool["name"]: tool for tool in document["tools"]}
    directories = sorted(
        directory
        for directory in dest.iterdir()
        if directory.is_dir() and not directory.name.startswith(".")
    )
    for directory in directories:
        entry = entries.get(directory.name)
        if entry is None:
            problems.append(f"{directory.name}: missing manifest entry")
            continue
        digest = f"sha256:{tree_digest(directory)}"
        if digest != entry["digest"]:
            problems.append(
                f"{directory.name}: digest mismatch ({digest} != {entry['digest']})"
            )
        for path, label, line in scan_tree(directory, rules):
            location = f"{directory.name}/{path}:{line}" if line else f"{directory.name}/{path}"
            problems.append(f"{location}: {label}")
    for name in sorted(set(entries) - {directory.name for directory in directories}):
        problems.append(f"{name}: manifest entry without a mirror directory")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="source Git repository")
    parser.add_argument("--name", help="public mirror name (default: source directory)")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--force", action="store_true", help="replace an existing mirror")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="verify existing mirrors instead of exporting",
    )
    args = parser.parse_args()
    rules = load_rules()

    if args.verify:
        problems = verify_mirrors(args.dest, rules)
        for problem in problems:
            print(problem)
        if problems:
            return 1
        print(f"mirror verification passed for {args.dest}")
        return 0

    if args.source is None:
        parser.error("--source is required unless --verify is used")
    source = args.source.resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    name = args.name or source.name
    status = run_git(source, "status", "--porcelain").decode().strip()
    if status:
        print("warning: source has uncommitted changes; exporting HEAD only")
    entry, staging_parent = write_mirror(source, name, args.dest, rules)
    install_mirror(staging_parent, name, args.dest, args.force)
    refresh_manifest(args.dest, entry)
    print(
        f"exported {name} at {entry['revision']} "
        f"({entry['files']} files, {entry['digest']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
