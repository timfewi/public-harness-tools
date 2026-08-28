#!/usr/bin/env python3
"""Validate the complete public skill catalog using only the Python standard library."""

from __future__ import annotations

import json
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
ROUTING_CASES = ROOT / "tests" / "routing-cases.json"
NEW_PUBLIC_SKILLS = {
    "release-engineering",
    "ci-workflows",
    "dependency-maintenance",
    "test-and-regression",
    "database-migrations",
    "performance-profiling",
    "wasm-component-engineering",
}
EXPECTED_COLLISIONS = {
    "release-engineering": [
        "ci-workflows",
        "dependency-maintenance",
        "wasm-component-engineering",
    ],
    "ci-workflows": ["test-and-regression", "release-engineering"],
    "dependency-maintenance": [
        "release-engineering",
        "wasm-component-engineering",
    ],
    "test-and-regression": ["ci-workflows", "performance-profiling"],
    "database-migrations": ["performance-profiling", "release-engineering"],
    "performance-profiling": ["test-and-regression", "database-migrations"],
    "wasm-component-engineering": [
        "release-engineering",
        "dependency-maintenance",
        "performance-profiling",
    ],
}
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)", re.DOTALL)
RESOURCE_RE = re.compile(
    r"(?<![A-Za-z0-9_/])((?:scripts|references|assets)/[A-Za-z0-9._/-]+)"
)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD|PLACEHOLDER)\b|lorem ipsum|as an AI|generated prose",
    re.IGNORECASE,
)
METADATA_RE = re.compile(
    r'\Ainterface:\n'
    r'  display_name: "([^"\n]+)"\n'
    r'  short_description: "([^"\n]+)"\n'
    r'  default_prompt: "([^"\n]+)"\n?\Z'
)
ALLOWED_RESOURCE_DIRS = {"agents", "scripts", "references", "assets"}
FORBIDDEN_PARTS = {
    ".git",
    ".direnv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
}
FORBIDDEN_SUFFIXES = {".log", ".tmp", ".swp", ".bak", ".pyc"}
FORBIDDEN_NAMES = {
    ".env",
    ".envrc",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "credentials",
    "credentials.json",
    "secrets.json",
}


def skill_directories(skills_dir: Path = SKILLS_DIR) -> list[Path]:
    if not skills_dir.is_dir():
        return []
    return sorted(path for path in skills_dir.iterdir() if path.is_dir())


def parse_frontmatter(text: str, source: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return {}, [f"{source}: missing strict opening YAML frontmatter block"]

    delimiter_count = len(re.findall(r"(?m)^---$", text))
    if delimiter_count != 2:
        errors.append(
            f"{source}: expected exactly two frontmatter delimiters, found {delimiter_count}"
        )

    fields: list[tuple[str, str]] = []
    for line in match.group("body").splitlines():
        if ": " not in line:
            errors.append(f"{source}: invalid frontmatter line: {line!r}")
            continue
        key, value = line.split(": ", 1)
        if not key or not value:
            errors.append(f"{source}: empty frontmatter key or value")
            continue
        fields.append((key, value))

    keys = [key for key, _ in fields]
    if keys != ["name", "description"]:
        errors.append(
            f"{source}: frontmatter keys must be exactly name, description in that order"
        )
    if len(set(keys)) != len(keys):
        errors.append(f"{source}: duplicate frontmatter key")

    remainder = text[match.end() :]
    if re.match(
        r"\A\s*---\n(?:(?:name|description):[^\n]*\n)+---(?:\n|\Z)",
        remainder,
    ):
        errors.append(f"{source}: second frontmatter-like block follows the first")

    return dict(fields), errors


def parse_metadata(text: str, source: Path) -> tuple[dict[str, str], list[str]]:
    match = METADATA_RE.match(text)
    if match is None:
        return {}, [
            f"{source}: metadata must contain only interface display_name, "
            "short_description, and default_prompt"
        ]
    display_name, short_description, default_prompt = match.groups()
    return {
        "display_name": display_name,
        "short_description": short_description,
        "default_prompt": default_prompt,
    }, []


def validate_routing(path: Path = ROUTING_CASES) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{path}: missing routing cases"]
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]

    if data.get("collision_matrix") != EXPECTED_COLLISIONS:
        errors.append(f"{path}: collision matrix does not match the required neighbors")

    execution = data.get("execution")
    if not isinstance(execution, dict):
        errors.append(f"{path}: missing routing execution record")
    else:
        expected_execution = {
            "query_count": 56,
            "positive_cases": 21,
            "negative_cases": 21,
            "ambiguous_cases": 14,
            "specialized_candidate_cases_retrieved": 54,
            "specialized_candidate_cases_expected": 54,
            "semantically_reviewed_cases": 56,
            "passed_cases": 56,
            "result": "pass",
        }
        for key, expected in expected_execution.items():
            if execution.get(key) != expected:
                errors.append(
                    f"{path}: routing execution {key} must be {expected!r}"
                )
        if not isinstance(execution.get("notes"), list) or not execution["notes"]:
            errors.append(f"{path}: routing execution notes are missing")

    routing_skills = data.get("skills")
    if not isinstance(routing_skills, dict) or set(routing_skills) != NEW_PUBLIC_SKILLS:
        errors.append(f"{path}: routing cases must cover exactly the seven new skills")
        return errors

    required_fields = {
        "id",
        "request",
        "expected_selected_skills",
        "expected_non_selected_skills",
        "first_tools_or_evidence",
        "unnecessary_or_forbidden_tools",
        "completion_condition",
        "stop_condition",
        "observed_selected_skills",
        "result",
    }
    seen_ids: set[str] = set()
    for skill_name in sorted(NEW_PUBLIC_SKILLS):
        groups = routing_skills[skill_name]
        if set(groups) != {"positive", "negative", "ambiguous"}:
            errors.append(f"{path}: {skill_name} must define positive, negative, ambiguous")
            continue
        expected_counts = {"positive": 3, "negative": 3, "ambiguous": 2}
        for group_name, expected_count in expected_counts.items():
            cases = groups[group_name]
            if not isinstance(cases, list) or len(cases) != expected_count:
                errors.append(
                    f"{path}: {skill_name} {group_name} must have {expected_count} cases"
                )
                continue
            for case in cases:
                if not isinstance(case, dict) or set(case) != required_fields:
                    errors.append(
                        f"{path}: {skill_name} {group_name} case fields are incomplete"
                    )
                    continue
                case_id = case["id"]
                if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
                    errors.append(f"{path}: invalid or duplicate routing case id {case_id!r}")
                seen_ids.add(case_id)
                scalar_fields = {
                    "request",
                    "completion_condition",
                    "stop_condition",
                    "result",
                }
                if any(
                    not isinstance(case[field], str) or not case[field].strip()
                    for field in scalar_fields
                ):
                    errors.append(f"{path}: {case_id} has an empty scalar field")
                list_fields = required_fields - scalar_fields - {"id"}
                if any(
                    not isinstance(case[field], list)
                    or not case[field]
                    or not all(isinstance(value, str) and value for value in case[field])
                    for field in list_fields
                ):
                    errors.append(f"{path}: {case_id} has an empty or invalid list field")
                    continue
                selected = set(case["expected_selected_skills"])
                not_selected = set(case["expected_non_selected_skills"])
                if selected & not_selected:
                    errors.append(f"{path}: {case_id} selects and rejects the same skill")
                if group_name == "positive" and skill_name not in selected:
                    errors.append(f"{path}: {case_id} positive case does not select {skill_name}")
                if group_name == "negative" and skill_name not in not_selected:
                    errors.append(f"{path}: {case_id} negative case does not reject {skill_name}")
                if group_name == "ambiguous":
                    neighbors = set(EXPECTED_COLLISIONS[skill_name])
                    if not (selected | not_selected) & neighbors:
                        errors.append(f"{path}: {case_id} does not exercise a neighbor")
                if case["result"] != "pass":
                    errors.append(f"{path}: {case_id} has not passed routing execution")
                observed = set(case["observed_selected_skills"])
                if not selected.issubset(observed):
                    errors.append(
                        f"{path}: {case_id} did not observe all expected selected skills"
                    )
                if observed & not_selected:
                    errors.append(
                        f"{path}: {case_id} observed a forbidden/non-selected skill"
                    )
    return errors


def validate_catalog(
    skills_dir: Path = SKILLS_DIR, routing_path: Path = ROUTING_CASES
) -> tuple[list[str], int]:
    errors: list[str] = []
    directories = skill_directories(skills_dir)
    for directory in directories:
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{directory}: missing SKILL.md")
            continue
        if skill_file.is_symlink():
            errors.append(f"{skill_file}: symbolic links are not allowed")
            continue

        text = skill_file.read_text(encoding="utf-8")
        frontmatter, frontmatter_errors = parse_frontmatter(text, skill_file)
        errors.extend(frontmatter_errors)
        skill_name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        if skill_name != directory.name:
            errors.append(
                f"{skill_file}: frontmatter name {skill_name!r} != directory {directory.name!r}"
            )
        if not NAME_RE.fullmatch(skill_name):
            errors.append(f"{skill_file}: invalid catalog name {skill_name!r}")
        if len(description) < 50 or not description.endswith("."):
            errors.append(f"{skill_file}: description is incomplete")
        if skill_name in NEW_PUBLIC_SKILLS and (
            "Use for" not in description or "not for" not in description
        ):
            errors.append(
                f"{skill_file}: new-skill description lacks complete use/not-for triggers"
            )
        if PLACEHOLDER_RE.search(text):
            errors.append(f"{skill_file}: placeholder or accidental generated prose found")

        metadata_file = directory / "agents" / "openai.yaml"
        if not metadata_file.is_file():
            errors.append(f"{metadata_file}: missing metadata")
        else:
            metadata, metadata_errors = parse_metadata(
                metadata_file.read_text(encoding="utf-8"), metadata_file
            )
            errors.extend(metadata_errors)
            if metadata:
                if not 12 <= len(metadata["short_description"]) <= 64:
                    errors.append(
                        f"{metadata_file}: short_description must be 12-64 characters"
                    )
                if f"${skill_name}" not in metadata["default_prompt"]:
                    errors.append(
                        f"{metadata_file}: default_prompt must invoke ${skill_name}"
                    )

        mentioned_resources = {
            match.group(1).rstrip(".,:;")
            for match in RESOURCE_RE.finditer(text)
        }
        actual_resources: set[str] = set()
        for item in sorted(directory.rglob("*")):
            relative = item.relative_to(directory)
            if item.is_symlink():
                errors.append(f"{item}: symbolic links are not allowed")
                continue
            if not item.is_file():
                continue
            if any(part in FORBIDDEN_PARTS for part in relative.parts):
                errors.append(f"{item}: forbidden generated or local state")
            if item.name in FORBIDDEN_NAMES or item.name.startswith(".env."):
                errors.append(f"{item}: forbidden credential or local configuration")
            if item.suffix in FORBIDDEN_SUFFIXES:
                errors.append(f"{item}: forbidden temporary or log file")
            if relative.name == "SKILL.md":
                continue
            if relative.parts[0] not in ALLOWED_RESOURCE_DIRS:
                errors.append(f"{item}: file is outside approved skill resource paths")
                continue
            if relative.as_posix() != "agents/openai.yaml":
                actual_resources.add(relative.as_posix())
            if item.suffix == ".sh" and not (item.stat().st_mode & stat.S_IXUSR):
                errors.append(f"{item}: shell script is not executable")

        for reference in sorted(mentioned_resources):
            if not (directory / reference).is_file():
                errors.append(f"{skill_file}: referenced resource does not exist: {reference}")
        for resource in sorted(actual_resources - mentioned_resources):
            errors.append(f"{skill_file}: bundled resource is not referenced: {resource}")

    errors.extend(validate_routing(routing_path))
    return errors, len(directories)


def main() -> int:
    errors, count = validate_catalog()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"catalog validation failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"catalog validation passed: {count} skills")
    print("frontmatter, names, metadata, resources, routing cases: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
