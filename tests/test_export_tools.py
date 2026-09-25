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

    def test_export_refuses_forbidden_relative_paths(self) -> None:
        repository = make_repository(self.base)
        for relative in ("skills-library.txt", "notes/nixos-host/clean.txt"):
            with self.subTest(relative=relative):
                path = repository / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("clean content\n", encoding="utf-8")
                commit(repository)
                dest = self.base / "dest"
                with self.assertRaisesRegex(ValueError, "forbidden path"):
                    write_mirror(repository, "example-tool", dest, RULES)
                self.assertFalse(list(dest.iterdir()))
                path.unlink()

    def test_export_refuses_forbidden_mirror_name(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("clean content\n", encoding="utf-8")
        commit(repository)
        with self.assertRaisesRegex(ValueError, "mirror name violates policy"):
            write_mirror(repository, "skills-library", self.base / "dest", RULES)

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

    def test_export_refuses_email_allowlist_suffix_spoof(self) -> None:
        repository = make_repository(self.base)
        for address in (
            "fixture@notexample.com",
            "fixture@fakeusers.noreply.github.com",
        ):
            with self.subTest(address=address):
                (repository / "contact.md").write_text(address + "\n", encoding="utf-8")
                commit(repository)
                with self.assertRaisesRegex(ValueError, "unexpected email domain"):
                    write_mirror(repository, "example-tool", self.base / "dest", RULES)

    def test_export_allows_exact_and_subdomain_emails(self) -> None:
        repository = make_repository(self.base)
        (repository / "contact.md").write_text(
            "contact fixture@example.com or fixture@alerts.example.com\n",
            encoding="utf-8",
        )
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        self.assertEqual(verify_mirrors(dest, RULES), [])

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

    def test_verify_refuses_forbidden_relative_path_with_updated_digest(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)
        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        mirror = dest / "example-tool"
        (mirror / "a.txt").rename(mirror / "skills-library.txt")
        refresh_manifest(dest, entry)

        self.assertTrue(
            any(
                "skills-library.txt" in problem and "forbidden path" in problem
                for problem in verify_mirrors(dest, RULES)
            )
        )

    def test_verify_refuses_tampered_manifest_fields(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)
        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        manifest = dest / "manifest.json"
        original = json.loads(manifest.read_text(encoding="utf-8"))
        for field, value, expected in (
            ("files", 2, "file count mismatch"),
            ("files", "1", "invalid files"),
            ("revision", "tampered", "invalid revision"),
            ("upstream", "", "invalid upstream"),
            ("upstream", "other-tool", "invalid upstream"),
            ("digest", "sha256:bad", "invalid digest"),
            ("name", "other-tool", "manifest entry without a mirror directory"),
        ):
            with self.subTest(field=field, value=value):
                document = json.loads(json.dumps(original))
                document["tools"][0][field] = value
                manifest.write_text(json.dumps(document), encoding="utf-8")
                self.assertTrue(
                    any(expected in problem for problem in verify_mirrors(dest, RULES))
                )
        document = json.loads(json.dumps(original))
        document["tools"].append(document["tools"][0].copy())
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.assertTrue(any("duplicate" in p for p in verify_mirrors(dest, RULES)))
        manifest.write_text('{"schema": "public-tool-mirror.v1", "tools": null}')
        self.assertTrue(any("invalid tools list" in p for p in verify_mirrors(dest, RULES)))
        manifest.write_text("{", encoding="utf-8")
        self.assertTrue(any("invalid manifest" in p for p in verify_mirrors(dest, RULES)))

    def test_verify_refuses_manifest_policy_and_extra_fields(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("clean content\n", encoding="utf-8")
        commit(repository)
        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        manifest = dest / "manifest.json"
        original = json.loads(manifest.read_text(encoding="utf-8"))
        for field, value in (
            ("upstream", "example/skills-library"),
            ("name", "skills-library"),
        ):
            with self.subTest(field=field):
                document = json.loads(json.dumps(original))
                document["tools"][0][field] = value
                manifest.write_text(json.dumps(document), encoding="utf-8")
                self.assertTrue(
                    any("violates policy" in problem for problem in verify_mirrors(dest, RULES))
                )
        document = json.loads(json.dumps(original))
        document["extra"] = "private metadata"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.assertTrue(any("unexpected manifest fields" in p for p in verify_mirrors(dest, RULES)))
        document = json.loads(json.dumps(original))
        document["tools"][0]["extra"] = "private metadata"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.assertTrue(
            any("unexpected manifest entry fields" in p for p in verify_mirrors(dest, RULES))
        )

    def test_verify_refuses_forbidden_mirror_root(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("clean content\n", encoding="utf-8")
        commit(repository)
        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        (dest / "example-tool").rename(dest / "skills-library")
        manifest = dest / "manifest.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["tools"][0]["name"] = "skills-library"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.assertTrue(
            any("mirror root violates policy" in problem for problem in verify_mirrors(dest, RULES))
        )

    def test_verify_refuses_unlisted_root_files_and_symlinks(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)
        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        self.assertEqual(verify_mirrors(dest, RULES), [])

        (dest / "extra.txt").write_text("unlisted\n", encoding="utf-8")
        (dest / ".hidden").write_text("unlisted\n", encoding="utf-8")
        (dest / "linked-file").symlink_to(dest / "example-tool" / "a.txt")
        (dest / "linked-dir").symlink_to(dest / "example-tool", target_is_directory=True)
        for name in ("extra.txt", ".hidden", "linked-file", "linked-dir"):
            self.assertTrue(any(name in p for p in verify_mirrors(dest, RULES)), name)

    def test_verify_refuses_post_export_symlinks(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        mirror = dest / "example-tool"

        # A dangling symlink does not affect the existing digest; its target
        # name is not read as file content by the scanner.
        (mirror / "link.txt").symlink_to("gh" + "p_" + "x" * 24)
        problems = verify_mirrors(dest, RULES)
        self.assertTrue(
            any("link.txt" in problem and "symlink" in problem for problem in problems)
        )

        (mirror / "link.txt").unlink()
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("gh" + "p_" + "x" * 24)
        (mirror / "link.txt").symlink_to(outside / "secret.txt")
        (mirror / "linked-dir").symlink_to(outside, target_is_directory=True)
        problems = verify_mirrors(dest, RULES)
        for name in ("link.txt", "linked-dir"):
            self.assertTrue(
                any(name in problem and "symlink" in problem for problem in problems)
            )
        self.assertFalse(any("credential pattern" in problem for problem in problems))
        with self.assertRaisesRegex(ValueError, "symlink"):
            refresh_manifest(dest, entry)

    def test_verify_refuses_symlinked_mirror_root(self) -> None:
        repository = make_repository(self.base)
        (repository / "a.txt").write_text("alpha\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        refresh_manifest(dest, entry)
        (dest / "example-tool").rename(self.base / "outside")
        (dest / "example-tool").symlink_to(self.base / "outside", target_is_directory=True)

        self.assertTrue(
            any("symlink" in problem for problem in verify_mirrors(dest, RULES))
        )

    def test_verify_refuses_spoofed_domain_even_with_updated_digest(self) -> None:
        repository = make_repository(self.base)
        (repository / "contact.md").write_text("fixture@example.com\n", encoding="utf-8")
        commit(repository)

        dest = self.base / "dest"
        entry, staging = write_mirror(repository, "example-tool", dest, RULES)
        install_mirror(staging, "example-tool", dest, force=False)
        (dest / "example-tool" / "contact.md").write_text(
            "fixture@notexample.com\n", encoding="utf-8"
        )
        refresh_manifest(dest, entry)
        self.assertTrue(
            any(
                "unexpected email domain" in problem
                for problem in verify_mirrors(dest, RULES)
            )
        )

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
