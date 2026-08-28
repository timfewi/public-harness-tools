#!/usr/bin/env python3
"""Create a deterministic allowlist-only archive of public skill content."""

from __future__ import annotations

import argparse
import gzip
import io
import tarfile
from pathlib import Path, PurePosixPath

from validate_catalog import (
    ALLOWED_RESOURCE_DIRS,
    FORBIDDEN_NAMES,
    FORBIDDEN_PARTS,
    FORBIDDEN_SUFFIXES,
    ROOT,
    SKILLS_DIR,
    skill_directories,
    validate_catalog,
)


def approved_skill_file(relative: Path) -> bool:
    parts = relative.parts
    if (
        any(part in FORBIDDEN_PARTS for part in parts)
        or relative.name in FORBIDDEN_NAMES
        or relative.name.startswith(".env.")
        or relative.suffix in FORBIDDEN_SUFFIXES
    ):
        return False
    if parts == ("SKILL.md",):
        return True
    if parts == ("agents", "openai.yaml"):
        return True
    return len(parts) >= 2 and parts[0] in ALLOWED_RESOURCE_DIRS - {"agents"}


def archive_files() -> list[Path]:
    files: list[Path] = []
    for directory in skill_directories():
        for path in sorted(directory.rglob("*")):
            if path.is_file() and approved_skill_file(path.relative_to(directory)):
                files.append(path)
    return files


def approved_archive_member(name: str, skill_names: set[str]) -> bool:
    path = PurePosixPath(name)
    parts = path.parts
    if path.is_absolute() or ".." in parts or len(parts) < 3:
        return False
    if parts[0] != "skills" or parts[1] not in skill_names:
        return False
    relative = Path(*parts[2:])
    return approved_skill_file(relative)


def build_archive(output: Path) -> list[str]:
    errors, _ = validate_catalog()
    if errors:
        joined = "\n".join(errors)
        raise ValueError(f"catalog validation failed before export:\n{joined}")

    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"output parent does not exist: {output.parent}")

    output_resolved_parent = output.parent.resolve()
    if output_resolved_parent == SKILLS_DIR.resolve() or SKILLS_DIR.resolve() in output_resolved_parent.parents:
        raise ValueError("archive output must not be inside a skill directory")

    files = archive_files()
    skill_names = {directory.name for directory in skill_directories()}
    member_names = [path.relative_to(ROOT).as_posix() for path in files]
    invalid = [
        name for name in member_names if not approved_archive_member(name, skill_names)
    ]
    if invalid:
        raise ValueError(f"export member escaped the allowlist: {invalid}")

    with output.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT
            ) as archive:
                for path, name in zip(files, member_names, strict=True):
                    data = path.read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                    archive.addfile(info, io.BytesIO(data))

    with tarfile.open(output, "r:gz") as archive:
        listed = archive.getnames()
    if listed != member_names:
        output.unlink(missing_ok=True)
        raise ValueError("archive listing differs from the deterministic member list")
    if any(not approved_archive_member(name, skill_names) for name in listed):
        output.unlink(missing_ok=True)
        raise ValueError("archive contains a member outside approved skill paths")
    return listed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="new .tar.gz output path")
    args = parser.parse_args()
    members = build_archive(args.output)
    for member in members:
        print(member)
    print(f"export verified: {len(members)} allowlisted files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
