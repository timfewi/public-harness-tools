"""Validate every template directory and its .project-checks.json contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = ("flake.nix", ".project-checks.json", "AGENTS.md", ".envrc", ".gitignore", "Justfile")
NAME = re.compile(r"[a-z][a-z0-9-]*")


def check_manifest(path: Path) -> None:
    document = json.loads(path.read_text())
    if not isinstance(document, dict) or document.get("version") != 1:
        raise SystemExit(f"{path}: version 1 required")
    checks = document.get("checks")
    if not isinstance(checks, list) or not checks:
        raise SystemExit(f"{path}: checks must be a nonempty array")
    names = set()
    for check in checks:
        name = check.get("name")
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
            raise SystemExit(f"{path}: invalid or duplicate check name {name!r}")
        names.add(name)
        argv = check.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise SystemExit(f"{path}: {name}.argv must be a nonempty string array")
        requires = check.get("requires")
        if not isinstance(requires, list) or not requires or not all(isinstance(x, str) and x for x in requires):
            raise SystemExit(f"{path}: {name}.requires must be a nonempty string array")
        profiles = check.get("profiles")
        if not isinstance(profiles, list) or not profiles or set(profiles) - {"fast", "full"}:
            raise SystemExit(f"{path}: {name}.profiles must be a subset of fast/full")


def check_project_policy(root: Path) -> None:
    """The three templates must share one Project policy, not three copies."""
    policies = {
        name: (root / name / "files" / "AGENTS.md").read_text()
        for name in ("default", "python", "rust")
    }
    if policies["default"] != policies["python"]:
        raise SystemExit("default and python AGENTS.md must stay identical")
    common = policies["default"].splitlines()
    rust = policies["rust"].splitlines()
    remaining = iter(rust)
    if not all(line in remaining for line in common):
        raise SystemExit("rust AGENTS.md must keep every default policy line in order")
    if len(rust) - len(common) != 1:
        raise SystemExit("rust AGENTS.md must add exactly one line to the default policy")


def main() -> int:
    root = Path(sys.argv[1])
    templates = sorted(path for path in root.iterdir() if path.is_dir())
    if not templates:
        raise SystemExit("no templates found")
    for template in templates:
        base = template / "files"
        if not base.is_dir():
            raise SystemExit(f"{template.name}: files/ is missing")
        for name in REQUIRED:
            if not (base / name).is_file():
                raise SystemExit(f"{template.name}: {name} is missing")
        check_manifest(base / ".project-checks.json")
    check_project_policy(root)
    print(f"validated {len(templates)} templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
