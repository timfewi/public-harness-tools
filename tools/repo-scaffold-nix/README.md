# repo-scaffold-nix

Fail-closed scaffolder and flake templates for the files every repository should
carry: a pinned `flake.nix`, a `.project-checks.json`, `AGENTS.md`, `.envrc`,
`.gitignore` and a `Justfile`.

`project-check` decides whether a repository passes its checks; this repository
decides that the files declaring those checks exist in the first place. The two
compose: the template's checks use commands the `agent-toolbox` groups provide.

## Fail-closed design

- **No overwrite** without `--force`; every file is created with `O_EXCL`.
- **No partial repository**: any failure removes the files this run created and
  the directory if this run created it.
- **No Git history changes**: it never stages or commits. New directories get
  `git init` on `main` with hooks disabled and no template hooks.
- **No dangerous targets**: a named destination must not exist, must not be a
  symlink, must not sit inside an existing Git repository, and must not escape
  the current directory.
- **No invented checks**: only checks whose tools the templates can name are
  emitted; the manifest is validated by a check.

## Usage

```sh
# New repository in a new directory (git init, no commit).
project-scaffold myproject --template rust

# Existing repository: add only the missing files.
cd myproject && project-scaffold

# Report-only modes.
project-scaffold --check        # exit 1 when files are missing (CI/doctor)
project-scaffold --dry-run      # print the plan, write nothing
```

The template is detected from the project manifests (`Cargo.toml` → `rust`,
`pyproject.toml`/`setup.py` → `python`, otherwise `default`), or selected with
`--template`. UI repositories that an agent should run visual QA against use
`--template web` explicitly; the scaffolder never guesses a web framework.

## For agents

An agent with `project-scaffold` on `PATH` should use it instead of
hand-writing the declaring files or improvising a template copy:

| Need | Command |
| --- | --- |
| New repository | `project-scaffold <name> --template auto` |
| Add only missing files to the current project | `project-scaffold` |
| Machine-readable status | `project-scaffold --check --json` |
| Preview without writing | `project-scaffold --dry-run` |

`--check --json` prints `{"template": "...", "missing": [...]}` and exits 1
when files are missing, so a harness can detect an unscaffolded repository
without parsing text. `nix flake init` copies the same template files into a
new or empty directory, but it cannot add only the missing files to an existing
project, report status, or roll back a partial copy; prefer the CLI for
existing repositories.

The companion `skill-library` repository owns the `repo-scaffold` skill, and
`coding-agents-nix` ships an opt-in guard that denies `nix flake init` and names
this command.

## Flake templates

For a brand-new project the idiomatic route is Nix itself. `nix flake init`
never overwrites existing files.

```sh
nix flake new myproject -t github:<owner>/repo-scaffold-nix#rust
nix flake init -t github:<owner>/repo-scaffold-nix#default
```

| Template | Contents |
| --- | --- |
| `default` | Nix formatter, statix, deadnix, `nix flake check` |
| `rust` | `default` plus `cargo fmt`/`clippy`/`test` |
| `python` | `default` plus `ruff check`/`format` |
| `web` | `default` plus `.visual-qa.config.json` and the `.visual-qa/` ignore for visual QA |

## Integration with the runtime

**Do not auto-scaffold when a harness starts.** `agent-lite` binds all of
`~/code` read-write and starts in the code root, so there is no single target
repository; writing on launch would mutate unrelated work. The runtime should
only *detect* missing files and print a hint (`project-scaffold`), while the
operator runs the command. See the pitfall table in [AGENTS.md](AGENTS.md).

## Pitfalls this repository prevents

| Pitfall | Guard |
| --- | --- |
| Overwriting existing files | exclusive create, `--force` opt-in |
| Half-written repository | rollback of created files and directory |
| Nested/clashing Git repository | refuse non-empty/nested/symlink targets |
| Accidental staging or commit | never stages; `git init` with `core.hooksPath=/dev/null` |
| Unpinned Nixpkgs | a concrete revision in every template |
| Flake ignoring the scaffold | `.envrc` uses `use flake path:.` until files are staged |
| Unsatisfiable `requires` | checks name only tools the toolbox provides |
| Wrong language detection | manifest-based detection, `default` fallback, no invented tests |
| Secrets in the repository | `.gitignore` per language, no credentials written |

## Agents do not load direnv

direnv's hook is prompt-driven — "Before each prompt it checks for the existence
of an `.envrc` file in the current and parent directories" — so non-interactive
agent shells do not load it. Claude Code's Bash tool does not source `~/.bashrc`
and direnv installs a `PROMPT_COMMAND` hook, so the hook never fires. The
supported non-interactive routes are:

- `nix develop -c <argv>` per command, or
- `direnv exec <dir> <argv>` for a whole harness, resolving the shell once per
  session rather than per command. Note: `direnv exec` takes `DIR COMMAND
  [ARGS...]` and supports no `--` separator.

The scaffold's `.envrc` is therefore for interactive use and editors, not for
agent correctness. Agents get their tools from the `agent-toolbox` groups or
from `nix develop -c`.

## Checks

```sh
nix flake check              # python tests, template integrity, statix/deadnix
python3 -m unittest discover -s tests -t . -p 'test_*.py'
```

## Scope

`x86_64-linux`, pinned Nixpkgs, English source and documentation. Node/Bun
projects fall back to the `default` template because there is no generic,
safe-in-all-cases Node check yet; add language checks deliberately. The `web`
template adds the visual QA configuration for UI repositories without claiming
any framework-specific check.
