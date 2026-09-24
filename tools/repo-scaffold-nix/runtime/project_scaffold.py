"""Create the flake, checks and agent files of a repository, fail-closed.

Two modes:

- ``project-scaffold NAME`` creates a new directory (a standalone repository on
  ``main``) and copies the selected template into it.
- ``project-scaffold`` with no NAME adds only the missing files to the current
  directory, which is how an existing repository gets a manifest.

It never overwrites unless ``--force`` is given, never stages or commits, and
rolls back every file it created when anything goes wrong. ``--check`` and
``--dry-run`` report without writing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Substituted at package build time; the source checkout falls back to ./templates.
PACKAGED_TEMPLATES = Path("@templates@")

TEMPLATE_CHOICES = ("auto", "default", "rust", "python", "web")

# Detected manifest -> template. Unknown projects get the Nix-only template.
DETECTION = (
    ("Cargo.toml", "rust"),
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("setup.cfg", "python"),
)

# Files every repository is expected to carry after scaffolding.
EXPECTED = ("flake.nix", ".project-checks.json", "AGENTS.md")


def templates_root() -> Path:
    override = os.environ.get("PROJECT_SCAFFOLD_TEMPLATES")
    if override:
        return Path(override)
    if not str(PACKAGED_TEMPLATES).startswith("@"):
        return PACKAGED_TEMPLATES
    return Path(__file__).resolve().parent.parent / "templates"


def detect_template(root: Path) -> str:
    for manifest, template in DETECTION:
        if (root / manifest).is_file():
            return template
    return "default"


def template_files(root: Path) -> list[str]:
    base = root / "files"
    if not base.is_dir():
        raise ValueError(f"template is unavailable: {root.name}")
    found: list[str] = []
    for directory, directories, files in os.walk(base):
        directories.sort()
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(base)
            if relative.name == ".keep":
                continue
            found.append(str(relative))
    if not found:
        raise ValueError(f"template is empty: {root.name}")
    return found


def load_template(template: str) -> dict[str, bytes]:
    root = templates_root() / template
    return {name: (root / "files" / name).read_bytes() for name in template_files(root)}


def inside_git_repository(directory: Path) -> bool:
    git = shutil.which("git")
    if not git:
        raise ValueError("required program is missing: git")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    probe = subprocess.run(
        [git, "-C", str(directory), "rev-parse", "--git-dir"],
        env=environment,
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


def validate_name(name: str) -> None:
    if name in {"", ".", ".."} or "/" in name or "\\" in name:
        raise ValueError("NAME must be one directory name")


def plan_files(root: Path, files: dict[str, bytes], force: bool) -> list[tuple[str, bool]]:
    """Return (relative path, will_write) for every template file."""
    plan = []
    for name in sorted(files):
        target = root / name
        if target.is_symlink():
            raise ValueError(f"refusing to replace a symlink: {name}")
        exists = target.exists()
        if exists and not force:
            plan.append((name, False))
        else:
            plan.append((name, True))
    return plan


def write_files(root: Path, files: dict[str, bytes], plan: list[tuple[str, bool]]) -> list[Path]:
    written: list[Path] = []
    try:
        for name, will_write in plan:
            if not will_write:
                continue
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive create unless --force; a concurrent writer must lose.
            mode = "wb" if target.exists() else "xb"
            with target.open(mode) as stream:
                stream.write(files[name])
            written.append(target)
    except BaseException:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise
    return written


def git_init(directory: Path) -> None:
    git = shutil.which("git")
    if not git:
        raise ValueError("required program is missing: git")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    subprocess.run(
        [
            git,
            "-c",
            "core.hooksPath=/dev/null",
            "init",
            "--quiet",
            "--initial-branch=main",
            "--template=",
            str(directory),
        ],
        env=environment,
        check=True,
        stdin=subprocess.DEVNULL,
    )


def missing_files(root: Path, files: dict[str, bytes]) -> list[str]:
    return [name for name in sorted(files) if not (root / name).is_file()]


def print_plan(root: Path, plan: list[tuple[str, bool]]) -> None:
    for name, will_write in plan:
        action = "create" if will_write else "skip  "
        print(f"{action} {name}")


def check(json_output: bool, template: str = "auto") -> int:
    root = Path.cwd()
    template = detect_template(root) if template == "auto" else template
    names = missing_files(root, load_template(template))
    if json_output:
        print(json.dumps({"template": template, "missing": names}))
    else:
        for name in names:
            print(f"missing {name}")
    return 1 if names else 0


def run(arguments: argparse.Namespace) -> int:
    if arguments.check:
        return check(arguments.json, arguments.template)
    if arguments.name is not None:
        validate_name(arguments.name)
    directory = Path.cwd() / arguments.name if arguments.name else Path.cwd()

    creating = arguments.name is not None
    if creating:
        if directory.exists():
            raise ValueError("named destination already exists")
        if not directory.parent.is_dir():
            raise ValueError("destination parent does not exist")
        if inside_git_repository(directory.parent):
            raise ValueError("destination would be nested inside a Git repository")
    elif directory.is_symlink() or not directory.is_dir():
        raise ValueError("the current directory must be a real directory")

    template = arguments.template if arguments.template != "auto" else detect_template(directory)
    files = load_template(template)
    plan = plan_files(directory, files, arguments.force)
    if arguments.dry_run:
        print(f"template {template}")
        print_plan(directory, plan)
        return 0

    created_directory = creating and not directory.exists()
    if created_directory:
        directory.mkdir()
    written: list[Path] = []
    try:
        written = write_files(directory, files, plan)
        if creating:
            git_init(directory)
    except BaseException:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        if created_directory and directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
        raise

    print(f"template {template}")
    print_plan(directory, plan)
    if creating:
        print(f"Created repository on main: {directory.name}")
    print("Checks: project-check fast | project-check full")
    if not creating:
        print("Review the new files, then stage them explicitly; nothing was staged.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="create this directory; omit to add missing files in place")
    parser.add_argument("--template", choices=TEMPLATE_CHOICES, default="auto")
    parser.add_argument("--check", action="store_true", help="report missing files and exit 1 if any")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing")
    parser.add_argument("--force", action="store_true", help="overwrite existing template files")
    parser.add_argument("--json", action="store_true", help="machine-readable output for --check")
    arguments = parser.parse_args(argv)
    try:
        return run(arguments)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        if arguments.json:
            print(json.dumps({"status": "error", "error": str(error)}))
        else:
            print(f"project-scaffold: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
