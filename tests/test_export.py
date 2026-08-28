from __future__ import annotations

import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_public_skills import (  # noqa: E402
    approved_archive_member,
    archive_files,
    build_archive,
)
from validate_catalog import skill_directories  # noqa: E402


class PublicSkillExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".public-skill-export-test-"
        )
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name)
        self.skill_names = {directory.name for directory in skill_directories()}

    def test_export_is_deterministic_complete_and_allowlisted(self) -> None:
        first = self.base / "first.tar.gz"
        second = self.base / "second.tar.gz"
        first_members = build_archive(first)
        second_members = build_archive(second)

        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(first_members, second_members)
        expected = [path.relative_to(ROOT).as_posix() for path in archive_files()]
        self.assertEqual(first_members, expected)
        self.assertTrue(first_members)
        self.assertTrue(
            all(
                approved_archive_member(name, self.skill_names)
                for name in first_members
            )
        )
        with tarfile.open(first, "r:gz") as archive:
            self.assertEqual(archive.getnames(), first_members)
            self.assertTrue(all(member.isfile() for member in archive.getmembers()))

    def test_export_rejects_non_allowlisted_member_shapes(self) -> None:
        rejected = [
            ".git/config",
            ".direnv/state",
            "tests/routing-cases.json",
            "skills/example/.env",
            "skills/example/agents/extra.yaml",
            "skills/example/scripts/run.log",
            "skills/example/references/cache.tmp",
            "skills/example/assets/__pycache__/state",
            "skills/../private/SKILL.md",
        ]
        for name in rejected:
            with self.subTest(name=name):
                self.assertFalse(approved_archive_member(name, {"example"}))

        accepted = [
            "skills/example/SKILL.md",
            "skills/example/agents/openai.yaml",
            "skills/example/scripts/tool.sh",
            "skills/example/references/source.md",
            "skills/example/assets/template.txt",
        ]
        for name in accepted:
            with self.subTest(name=name):
                self.assertTrue(approved_archive_member(name, {"example"}))

    def test_existing_archive_collision_is_not_overwritten(self) -> None:
        output = self.base / "existing.tar.gz"
        output.write_bytes(b"unrelated")
        with self.assertRaises(FileExistsError):
            build_archive(output)
        self.assertEqual(output.read_bytes(), b"unrelated")


if __name__ == "__main__":
    unittest.main()
