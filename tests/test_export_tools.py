from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_public_tools import (  # noqa: E402
    MANIFEST_SCHEMA,
    install_mirror,
    load_rules,
    refresh_manifest,
    tree_digest,
    verify_mirrors,
    write_mirror,
)

RULES = load_rules()


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    )


def commit(repository: Path) -> None:
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "fixture")


def make_repository(base: Path, name: str = "example-tool") -> Path:
    repository = base / name
    repository.mkdir()
    git(repository, "init", "-q")
    git(repository, "config", "user.name", "fixture")
    git(repository, "config", "user.email", "fixture@users.noreply.github.com")
    return repository


class PublicToolExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="public-tool-export-test-")
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name)

    def test_export_uses_tracked_head_and_sanitizes(self) -> None:
        repository = make_repository(self.base)
        (repository / "README.md").write_text(
            "input git+ssh://git@github.com/timfewi/example-tool.git\n"
            "fixture /home/tim/src/parser.rs\n"
            "exclude tailscale-infra/\n",
            encoding="utf-8",
        )
        (repository / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
        (repository / ".envrc").write_text("use flake\n", encoding="utf-8")
        (repository / ".env").write_text("TOKEN=fixture\n", encoding="utf-8")
        (repository / "notes.log").write_text("scratch\n", encoding="utf-8")
        (repository / "dist").mkdir()
        (repository / "dist" / "out.bin").write_bytes(b"artifact")
        commit(repository)
        (repository / "untracked.txt").write_text("never exported\n", encoding="utf-8")

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        self.assertTrue(staging.is_dir())

        exported = {
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file()
        }
        self.assertEqual(exported, {"README.md", "AGENTS.md", ".envrc"})
        readme = (staging / "README.md").read_text(encoding="utf-8")
        self.assertIn("git+https://github.com/timfewi/example-tool.git", readme)
        self.assertIn("/home/user/src/parser.rs", readme)
        self.assertIn("exclude secrets/", readme)
        self.assertEqual(entry["files"], 3)
        self.assertEqual(entry["upstream"], "example-tool")
        self.assertEqual(
            entry["revision"],
            subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )

    def test_export_refuses_forbidden_content_without_partial_output(self) -> None:
        repository = make_repository(self.base)
        (repository / "notes.md").write_text(
            "see skills-library for the catalog\n", encoding="utf-8"
        )
        commit(repository)

        dest = self.base / "dest"
        with self.assertRaises(ValueError):
            write_mirror(repository, "example-tool", dest, RULES)
        self.assertFalse((dest / "example-tool").exists())
        self.assertFalse(
            [path for path in dest.iterdir() if path.name.startswith(".example-tool.")]
        )

    def test_export_refuses_symlinks(self) -> None:
        repository = make_repository(self.base)
        (repository / "target.txt").write_text("target\n", encoding="utf-8")
        os.symlink("target.txt", repository / "link.txt")
        commit(repository)

        with self.assertRaises(ValueError):
            write_mirror(repository, "example-tool", self.base / "dest", RULES)

    def test_export_refuses_credential_markers(self) -> None:
        repository = make_repository(self.base)
        (repository / "key.txt").write_text(
            "-----BEGIN " + "RSA PRIVATE KEY-----\n", encoding="utf-8"
        )
        commit(repository)

        with self.assertRaises(ValueError):
            write_mirror(repository, "example-tool", self.base / "dest", RULES)

    def test_export_refuses_unexpected_email_domains(self) -> None:
        repository = make_repository(self.base)
        (repository / "contact.md").write_text(
            "mail me at someone@gmail.com\n", encoding="utf-8"
        )
        commit(repository)

        with self.assertRaises(ValueError):
            write_mirror(repository, "example-tool", self.base / "dest", RULES)

    def test_export_is_deterministic(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        (repository / "b.txt").write_text("beta\n", encoding="utf-8")
        commit(repository)

        first, first_staging = write_mirror(
            repository, "example-tool", self.base / "one", RULES
        )
        second, second_staging = write_mirror(
            repository, "example-tool", self.base / "two", RULES
        )
        self.assertEqual(first["digest"], second["digest"])
        self.assertEqual(tree_digest(first_staging), tree_digest(second_staging))

    def test_verify_detects_drift_and_missing_entries(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        os.replace(staging, dest / "example-tool")
        refresh_manifest(dest, entry)
        self.assertEqual(verify_mirrors(dest, RULES), [])

        (dest / "example-tool" / "a.txt").write_text("drifted\n", encoding="utf-8")
        problems = verify_mirrors(dest, RULES)
        self.assertTrue(any("digest mismatch" in problem for problem in problems))

        (dest / "orphan").mkdir()
        (dest / "orphan" / "file.txt").write_text("x\n", encoding="utf-8")
        problems = verify_mirrors(dest, RULES)
        self.assertTrue(any("missing manifest entry" in problem for problem in problems))

    def test_existing_mirror_requires_force_and_cleans_staging(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)

        _, second_staging = write_mirror(repository, "example-tool", dest, RULES)
        with self.assertRaises(FileExistsError):
            install_mirror(second_staging, "example-tool", dest, force=False)
        self.assertFalse(second_staging.exists())
        self.assertEqual((dest / "example-tool" / "a.txt").read_text(), "alpha\n")

    def test_manifest_schema_and_digest_roundtrip(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        os.replace(staging, dest / "example-tool")
        refresh_manifest(dest, entry)

        document = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], MANIFEST_SCHEMA)
        self.assertEqual([tool["name"] for tool in document["tools"]], ["example-tool"])
        self.assertEqual(
            document["tools"][0]["digest"],
            f"sha256:{tree_digest(dest / 'example-tool')}",
        )


if __name__ == "__main__":
    unittest.main()
