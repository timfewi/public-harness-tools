# Working on agent-toolbox-nix

This repository is meant to be continued by OpenCode, Codex or another coding
assistant. No prior chat or assistant-specific attachment is required.

1. Read [`README.md`](README.md) for the purpose, [`docs/architecture.md`](docs/architecture.md)
   for the design and decisions, and [`docs/research.md`](docs/research.md) for the
   external evidence with source URLs.
2. Inspect `git status --short` and the staged/unstaged diffs before editing.
   Existing work must be preserved; never reset it.
3. Use the pinned shell: `nix develop` (it contains `nix`, `nixfmt` and the
   group tools).

## Scope

The repository is a **composition root**: it aggregates pinned tools into
selectable groups and exposes them through one stable argv. It is not a sandbox,
a runtime, a provider adapter or a policy engine. It does not depend on the
sibling tool flakes; a consuming host adds those packages through
`programs.agentToolbox.extraPackages`.

## Honesty rules

- A tool group is only as good as its check. Adding a package means adding it to
  a group and, when it is representative, naming its command in `commands`.
- Do not claim a boundary, isolation or authority that the repository does not
  implement. `PATH` is not a sandbox.
- Keep the tool surface stable and small. A new group needs a written reason in
  `docs/architecture.md`, not just a new package list.
- Prompt-cache claims must stay tied to the cited provider documentation. Do not
  invent measurements.

## Checks

Run the documented fast gate before reporting work:

```sh
nix flake check
nix fmt --no-write-lock-file -- --ci
```

`project-check fast|full` reads [`.project-checks.json`](.project-checks.json)
and runs the same commands with the installed shared runner.

`nix flake check` evaluates every group, the module options and the wrapper. It
does not build the full agent closure; build `.#agent-toolbox-light` when the
wrapper mechanism itself changed.

## Privacy

No credentials, personal paths, host names or account identifiers belong in the
repository or its documentation. Examples use synthetic values.
