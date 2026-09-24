# Working on repo-scaffold-nix

This repository is meant to be continued by OpenCode, Codex or another coding
assistant. No prior chat or assistant-specific attachment is required.

1. Read [`README.md`](README.md) for the guarantees and the pitfall table.
2. Inspect `git status --short` and the staged/unstaged diffs before editing.
   Existing work must be preserved; never reset it.
3. Use the pinned shell (`nix develop`) or the `agent-toolbox` groups.

## Scope

The command writes the files that declare a repository's checks; it does not run
them and does not own the `project-check` contract. Keep the Python runtime
standard-library-only, argv-only and fail-closed: exclusive creation, rollback,
and refusal of unsafe targets.

## Honesty rules

- A guard only exists if a test proves it. New refusal or rollback behavior
  needs a unit test.
- Do not emit a check the template cannot justify. Language templates only carry
  checks that are safe for every project of that language.
- Do not add write authority the command does not need; it must never stage,
  commit, push or publish.
- Keep the tool surface small: one command with `--check`, `--dry-run` and
  `--force`.

## Checks

```sh
nix flake check
python3 -m unittest discover -s tests -t . -p 'test_*.py'
```

`nix flake check` runs the Python contract tests, the template-integrity check
and the statix/deadnix lint gate.

## Privacy

No credentials, personal paths, host names or account identifiers belong in the
repository or its documentation. Examples use synthetic names.
