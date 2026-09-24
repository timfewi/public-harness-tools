# Giving agents a Nix development shell

The toolbox does not call `nix develop` per command. It materializes the
environment once with `pkgs.buildEnv` and exposes a stable wrapper. This page
records the alternatives and the pitfalls, so a project's own shell can be
combined with the toolbox deliberately.

## `nix develop` and non-interactive use

- `nix develop` runs a bash shell with the derivation's build environment.
  `-c`/`--command` runs one command instead. It takes a command plus arguments,
  with **no shell parsing**: `-c codex` works, but shell syntax needs an explicit
  shell, as in the official example
  `nix develop --command bash -c "mkdir build && cmake .. && make"`.
- A flake resolves `devShells.<system>.default` first, then
  `packages.<system>.default`; a named attribute is looked up in `devShells`,
  `packages`, then `legacyPackages`. That is why
  `nix develop github:openai/codex#codex-rs` still works even though the flake
  only defines the package.
- `nix print-dev-env` prints a script for the **current** shell instead of a
  subshell, and `--json` produces a machine-readable form. The manual's own
  example sources it (`. <(nix print-dev-env nixpkgs#hello)`), but sourcing runs
  the derivation's setup and `shellHook`, so only source the output of a flake
  you trust.

## Reuse the environment once per session

Running `nix develop -c` for every command is the expensive pattern: a local
flake is copied to the store before evaluation, and the eval cache only applies
to clean, source-controlled flakes — not to `path:` and not to a dirty work tree.
Resolve once, then reuse.

```sh
# Once per checkout: record the environment into a profile (a GC root).
nix develop --profile .direnv/dev-env <dir-or-installable>

# Per command: reuse the profile; the flake is not re-evaluated.
nix develop .direnv/dev-env -c <argv...>
```

- A profile symlink is a GC root: "Each of these symlinks is a root for the Nix
  garbage collector." Remove it to let the closure be collected.
- `nix print-dev-env --profile <path>` is the same mechanism with the sourceable
  output instead of a subshell.
- **nix-direnv does this automatically.** On a cache miss it runs
  `nix print-dev-env --profile <tmp>` and stores the emitted script in
  `.direnv/…-profile.rc`; on a hit it replays that file ("Using cached dev
  shell") without calling `nix` at all, and it installs GC roots with
  `nix build --out-link`. Manual reload mode plus `nix-direnv-reload`, or the
  `direnv-instant` daemon, avoid surprises.
- `direnv exec DIR COMMAND [ARGS...]` runs one command after loading the first
  `.envrc`. **There is no `--` separator**: use `direnv exec . codex`, not
  `direnv exec . -- codex` (the latter tries to run a command named `--`).

`nix develop <profile>` still starts bash, sources `stdenv/setup`, re-runs the
`shellHook` and sets `IN_NIX_SHELL`; it only skips flake evaluation. `direnv exec`
on a nix-direnv cache hit avoids `nix` entirely.

## `mkShell` versus wrappers

`mkShell` puts `packages` on `PATH`, turns string-coercible attributes into
environment variables and runs `shellHook` at entry. `mkShellNoCC` omits the
implicit C compiler. This repository uses `mkShell` only for `devShells`; the
agent-facing wrapper is a `buildEnv` plus a shell script, so it has no
`shellHook`, no implicit compiler and no per-call evaluation cost.

Higher-level managers add their own CLI and lockfiles:

- **numtide/devshell** builds a clean environment, supports declarative
  `commands`, `env` and `prefix` (a `PATH`-prepending variable), can suppress
  its interactive menu with `DEVSHELL_NO_MOTD=1`, and can re-expose a shell as a
  runnable package (`nix run '.#devshell' -- cmd`).
- **devenv** wraps Nix with `devenv shell`, `devenv up`, `devenv test`, a
  `devenv.lock` lockfile and language modules; it also ships `devenv mcp` and a
  documented Claude Code integration that tells the agent to run commands via
  `devenv shell -- …`.
- **flox** aims at users avoiding raw Nix, with `flox activate` and a manifest.
- **direnv + nix-direnv** auto-activates a shell on `cd` and caches/GC-roots it;
  nix-direnv uses `nix print-dev-env` under the hood.

For a non-interactive agent, the prebuilt toolbox plus a per-session
`nix develop --profile` (or nix-direnv) is the least surprising choice.

## Pitfalls

- **Flakes copy the repository to the store.** "Currently flakes are evaluated
  from the Nix store, so when using a local flake, it's first copied to the
  store." In a large repository this dominates; the issue report calls
  `nix develop` "pretty much unusable" there and notes "it's also not possible
  to cancel the copying … step". The eval cache does not help for `path:` or a
  dirty work tree.
- **direnv is not active in non-interactive shells.** Its hook is prompt-driven
  ("Before each prompt it checks for the existence of an `.envrc`"), and Claude
  Code's Bash tool does not source `~/.bashrc`. Do not make agent correctness
  depend on `.envrc`; use `nix develop -c` or `direnv exec`.
- **`shellHook` runs on every instantiation**, including `nix develop <profile>`
  and each `print-dev-env`. Keep dev-shell hooks idempotent and cheap.
- **nix-direnv can silently fall back to a stale shell** when a new evaluation
  fails (disable with `nix_direnv_disallow_fallback`), and it needs Nix on
  `PATH` (`NIX_DIRENV_FALLBACK_NIX`).
- **Impure shells are an escape hatch.** `--impure` "Allow access to mutable
  paths and repositories" and disables the hermeticity that makes the eval cache
  reliable. Flakes are pure by default; prefer pinned inputs.
- **`NIX_PATH` lookup.** `-I` beats the `nix-path` setting and `NIX_PATH`; flake
  builds avoid lookup paths by pinning inputs.
- **`IN_NIX_SHELL`.** Nix sets it, but the `nix develop` manual does not document
  the value; treat it as an implementation detail (current source hard-codes
  `impure`).

## Recommended combination

1. Use the toolbox as the always-present baseline for shell commands.
2. For a repository with its own `devShells`, resolve its shell **once** —
   `nix develop --profile .direnv/dev-env <dir>` (or let nix-direnv cache it) —
   and then run project commands from that profile.
3. Never run `nix develop -c` per command in a dirty or large repository.
4. Do not rely on direnv auto-activation for agent correctness; treat it as a
   convenience for interactive use.

## Evidence

Read through the isolated research service on 2026-09-18 and 2026-09-19:

- Nix manual 2.35, `nix develop`, `nix print-dev-env`, `nix profile`, `nix-shell`.
- nix.dev declarative-shell tutorial, direnv recipe, flakes concept.
- `numtide/devshell` README, getting-started, env, CI and flake-app docs.
- `devenv.sh` getting started and Claude Code integration; `flox.dev` docs.
- `nix-community/nix-direnv` README and `direnvrc`; direnv man page and
  `cmd_exec.go`.
- NixOS/nix issues #3121 (lazy flake copy), #7284 (large-repo latency and
  non-cancellable copy), #10437 (eval cache not used for dirty flakes), #10679
  (`shellHook` reruns).
