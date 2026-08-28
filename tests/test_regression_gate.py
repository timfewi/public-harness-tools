from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills" / "test-and-regression" / "scripts" / "regression-gate.sh"


class RegressionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".regression-gate-test-"
        )
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name)

    def run_gate(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(RUNNER), *map(str, arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_pass_mode_preserves_logs_statuses_and_exact_argv(self) -> None:
        artifact = self.base / "pass-artifacts"
        command = [sys.executable, "-c", "print('stable pass')"]
        result = self.run_gate("pass", "3", artifact, "--", *command)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("classification=all-pass", result.stdout)
        self.assertEqual(len(list(artifact.glob("run-*.log"))), 3)
        self.assertEqual(
            [path.read_text().strip() for path in sorted(artifact.glob("run-*.status"))],
            ["0", "0", "0"],
        )
        expected_argv = b"".join(os.fsencode(argument) + b"\0" for argument in command)
        self.assertEqual((artifact / "command.argv0").read_bytes(), expected_argv)
        self.assertIn("result=pass", (artifact / "summary.txt").read_text())

    def test_deterministic_fail_mode_checks_expected_signature(self) -> None:
        artifact = self.base / "fail-artifacts"
        command = [
            sys.executable,
            "-c",
            "import sys; print('EXPECTED-CODE-42', file=sys.stderr); raise SystemExit(7)",
        ]
        result = self.run_gate(
            "fail", "3", artifact, "--expect", "EXPECTED-CODE-42", "--", *command
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = (artifact / "summary.txt").read_text()
        self.assertIn("classification=all-fail", summary)
        self.assertIn("signature_mismatches=0", summary)
        self.assertEqual(
            [path.read_text().strip() for path in sorted(artifact.glob("run-*.status"))],
            ["7", "7", "7"],
        )

    def test_expected_signature_mismatch_fails(self) -> None:
        artifact = self.base / "mismatch-artifacts"
        command = [
            sys.executable,
            "-c",
            "import sys; print('actual signature', file=sys.stderr); raise SystemExit(2)",
        ]
        result = self.run_gate(
            "fail", "2", artifact, "--expect", "different signature", "--", *command
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "signature_mismatches=2", (artifact / "summary.txt").read_text()
        )
        self.assertIn("result=fail", result.stdout)

    def test_flake_mode_requires_mixed_outcomes(self) -> None:
        artifact = self.base / "flake-artifacts"
        state = self.base / "alternating-state"
        code = (
            "from pathlib import Path; import sys; p=Path(sys.argv[1]); "
            "exists=p.exists(); p.unlink() if exists else p.write_text('next'); "
            "print('INTERMITTENT-SIGNATURE', file=sys.stderr) if exists else None; "
            "raise SystemExit(9 if exists else 0)"
        )
        result = self.run_gate(
            "flake",
            "4",
            artifact,
            "--expect",
            "INTERMITTENT-SIGNATURE",
            "--",
            sys.executable,
            "-c",
            code,
            state,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = (artifact / "summary.txt").read_text()
        self.assertIn("classification=mixed", summary)
        self.assertIn("pass=2", summary)
        self.assertIn("fail=2", summary)

    def test_invalid_arguments_are_rejected_without_artifacts(self) -> None:
        cases = [
            ("invalid-mode", ["unknown", "1"]),
            ("nonnumeric-runs", ["pass", "abc"]),
            ("negative-runs", ["pass", "-1"]),
            ("excessive-runs", ["pass", "1001"]),
        ]
        for name, prefix in cases:
            with self.subTest(name=name):
                artifact = self.base / name
                result = self.run_gate(
                    *prefix,
                    artifact,
                    "--",
                    sys.executable,
                    "-c",
                    "raise SystemExit(0)",
                )
                self.assertEqual(result.returncode, 64)
                self.assertFalse(artifact.exists())

    def test_empty_command_is_rejected(self) -> None:
        artifact = self.base / "empty-command"
        result = self.run_gate("pass", "1", artifact, "--")
        self.assertEqual(result.returncode, 64)
        self.assertFalse(artifact.exists())

    def test_zero_runs_is_rejected(self) -> None:
        artifact = self.base / "zero-runs"
        result = self.run_gate(
            "pass",
            "0",
            artifact,
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(0)",
        )
        self.assertEqual(result.returncode, 64)
        self.assertFalse(artifact.exists())

    def test_artifact_path_safety_rejects_traversal_and_symlink_parent(self) -> None:
        traversal = self.base / "safe" / ".." / "escaped"
        result = self.run_gate(
            "pass",
            "1",
            traversal,
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(0)",
        )
        self.assertEqual(result.returncode, 64)
        self.assertFalse(self.base.joinpath("escaped").exists())

        target = self.base / "symlink-target"
        target.mkdir()
        link = self.base / "symlink-parent"
        link.symlink_to(target, target_is_directory=True)
        linked_artifact = link / "artifacts"
        result = self.run_gate(
            "pass",
            "1",
            linked_artifact,
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(0)",
        )
        self.assertEqual(result.returncode, 64)
        self.assertFalse((target / "artifacts").exists())

    def test_existing_output_collision_preserves_existing_files(self) -> None:
        artifact = self.base / "existing-artifacts"
        artifact.mkdir()
        marker = artifact / "keep.txt"
        marker.write_text("unrelated evidence", encoding="utf-8")

        result = self.run_gate(
            "pass",
            "1",
            artifact,
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(0)",
        )

        self.assertEqual(result.returncode, 64)
        self.assertEqual(marker.read_text(encoding="utf-8"), "unrelated evidence")
        self.assertEqual(list(artifact.iterdir()), [marker])


if __name__ == "__main__":
    unittest.main()
