"""Contract tests for the fail-closed repository scaffolder."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime import project_scaffold


def git_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


class ScaffoldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(os.chdir, self.previous)
        self.templates = Path(__file__).resolve().parent.parent / "templates"
        patcher = mock.patch.dict(os.environ, {"PROJECT_SCAFFOLD_TEMPLATES": str(self.templates)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_new_directory_creates_files(self) -> None:
        self.assertEqual(project_scaffold.main(["project", "--template", "default"]), 0)
        target = self.root / "project"
        for name in ("flake.nix", ".project-checks.json", "AGENTS.md", ".envrc", ".gitignore", "Justfile"):
            self.assertTrue((target / name).is_file(), name)
        self.assertTrue((target / ".git").is_dir())
        self.assertFalse(any((target / ".git").glob("hooks/*.sample")))

    def test_refuses_nonempty_destination(self) -> None:
        (self.root / "project").mkdir()
        (self.root / "project" / "keep.txt").write_text("keep\n")
        self.assertEqual(project_scaffold.main(["project"]), 1)
        self.assertEqual((self.root / "project" / "keep.txt").read_text(), "keep\n")
        self.assertFalse((self.root / "project" / "flake.nix").exists())

    def test_refuses_nested_git_repository(self) -> None:
        subprocess.run(["git", "init", "--quiet", str(self.root)], env=git_environment(), check=True)
        self.assertEqual(project_scaffold.main(["project"]), 1)
        self.assertFalse((self.root / "project").exists())

    def test_in_place_adds_missing_only(self) -> None:
        (self.root / "AGENTS.md").write_text("existing\n")
        self.assertEqual(project_scaffold.main([]), 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "existing\n")
        self.assertTrue((self.root / "flake.nix").is_file())
        self.assertFalse((self.root / ".git").exists())
        self.assertIn("devShells", (self.root / "flake.nix").read_text())

    def test_check_reports_missing_then_passes(self) -> None:
        self.assertEqual(project_scaffold.main(["--check"]), 1)
        self.assertEqual(project_scaffold.main([]), 0)
        self.assertEqual(project_scaffold.main(["--check"]), 0)

    def test_dry_run_writes_nothing(self) -> None:
        before = set(self.root.iterdir())
        self.assertEqual(project_scaffold.main(["--dry-run"]), 0)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_auto_detects_rust(self) -> None:
        (self.root / "Cargo.toml").write_text("[package]\nname = \"demo\"\n")
        self.assertEqual(project_scaffold.main([]), 0)
        self.assertIn("cargo", (self.root / "flake.nix").read_text())
        manifest = (self.root / ".project-checks.json").read_text()
        self.assertIn("cargo-fmt", manifest)

    def test_auto_detects_python(self) -> None:
        (self.root / "pyproject.toml").write_text("[project]\nname = \"demo\"\n")
        self.assertEqual(project_scaffold.main([]), 0)
        manifest = (self.root / ".project-checks.json").read_text()
        self.assertIn("ruff-check", manifest)

    def test_force_overwrites(self) -> None:
        (self.root / "AGENTS.md").write_text("existing\n")
        self.assertEqual(project_scaffold.main([]), 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "existing\n")
        self.assertEqual(project_scaffold.main(["--force"]), 0)
        self.assertNotEqual((self.root / "AGENTS.md").read_text(), "existing\n")

    def test_refuses_symlink_target(self) -> None:
        (self.root / "outside").write_text("outside\n")
        (self.root / "flake.nix").symlink_to(self.root / "outside")
        self.assertEqual(project_scaffold.main([]), 1)
        self.assertEqual((self.root / "outside").read_text(), "outside\n")

    def test_stages_nothing(self) -> None:
        subprocess.run(["git", "init", "--quiet", str(self.root)], env=git_environment(), check=True)
        self.assertEqual(project_scaffold.main([]), 0)
        staged = subprocess.run(
            ["git", "-C", str(self.root), "diff", "--cached", "--name-only"],
            env=git_environment(),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(staged.stdout, "")

    def test_invalid_name(self) -> None:
        self.assertEqual(project_scaffold.main(["../escape"]), 1)
        self.assertEqual(project_scaffold.main(["a/b"]), 1)


if __name__ == "__main__":
    unittest.main()
