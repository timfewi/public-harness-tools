# agent-toolbox-nix

Pinned, modular tool environment and **single-argv toolbox** for coding agents.
One Nix flake gives an agent a complete, reproducible Linux toolset — search,
git, languages, LSP servers, linters, formatters — behind one stable program
name, so the agent's shell calls and its tool definitions stay constant.

This is not a sandbox. The toolbox puts pinned executables on `PATH`; it grants
no network, credentials, filesystem authority or isolation. Pair it with
`lite-runtime-nix` or `agent-runtime-nix` when a real boundary is required.

## Why

Coding agents usually get an inconsistent `PATH`: tools exist on the operator's
interactive shell but not in the harness worker, or one project has a toolchain
and the next does not. Two problems follow:

1. **Missing tools** — the agent silently falls back to weaker commands, or
   reports a missing executable as a blocker.
2. **Unstable tool surfaces** — adding, removing or reordering tools invalidates
   provider prompt caches. Anthropic documents that *modifying tool definitions
   (names, descriptions, parameters) invalidates the entire cache* and that
   caches are built in the order `tools → system → messages`; OpenAI documents
   that tool names, descriptions, schemas and **ordering** participate in the
   cached prefix. The MCP specification (2026-07-28) therefore requires servers
   to return tools in a *deterministic order* so clients can cache the tool list
   and keep prompt caches stable.

The toolbox answers both: every tool is present, and the agent talks to a single
stable program (`agent-toolbox <argv>`) whose interface never changes between
sessions. See [`docs/architecture.md`](docs/architecture.md) and
[`docs/research.md`](docs/research.md) for the evidence.

## Quick start

```sh
# Interactive shell with the full agent toolset.
nix develop

# One group only.
nix develop .#rust
nix develop .#lsp

# The materialized environment, all groups.
nix build .#agent-toolbox
```

Use the wrapper directly:

```sh
agent-toolbox rg -n 'needle' src
agent-toolbox git status --short
agent-toolbox --list        # every command in the environment
agent-toolbox --env         # the environment store path
```

## Tool groups

Groups are independent package lists selected by name. `agent` is the union,
`light` a small fallback. See [`docs/tool-groups.md`](docs/tool-groups.md).

| Group | Contents |
| --- | --- |
| `core` | shell, coreutils, grep/sed/awk, ripgrep, fd, jq, yq, sd, bat, eza, tree |
| `git` | git, git-lfs, gh, delta, tig |
| `nix` | nix, nixfmt, deadnix, statix, direnv, nix-direnv, age, sops |
| `search` | ripgrep, ast-grep, tree-sitter, universal-ctags, hyperfine, tokei |
| `rust` | rustc, cargo, clippy, rustfmt, rust-analyzer, cargo-nextest, sqlite |
| `node` | nodejs, bun, pnpm, yarn, typescript |
| `python` | python3, uv, ruff, basedpyright |
| `go` | go, gopls, gotools |
| `c` | gcc, clang, clang-tools, cmake, make, ninja, meson, lld, valgrind |
| `lsp` | rust-analyzer, typescript-language-server, basedpyright, nixd, nil, gopls, taplo, yaml/bash/lua language servers, clangd |
| `lint` | shellcheck, luacheck, ruff, eslint, prettier, biome, yamllint, hadolint, actionlint, semgrep, osv-scanner, gitleaks |
| `wasm` | wasmtime, wasm-tools, wit-bindgen, cargo-component |
| `proto` | protobuf, buf, grpcurl, protobuf-language-server |
| `runtime` | bubblewrap, util-linux, procps, just |

## NixOS module

```nix
{
  inputs.agent-toolbox.url = "git+https://github.com/<owner>/agent-toolbox-nix.git?ref=main";
  imports = [ inputs.agent-toolbox.nixosModules.default ];

  programs.agentToolbox = {
    enable = true;
    groups = [ "core" "git" "rust" "lsp" "lint" ];  # empty = agent union
    extraPackages = [
      # Sibling private tools stay host-provided.
      ast-index.packages.x86_64-linux.ast-index
      project-check.packages.x86_64-linux.project-check
      agent-security-scan.packages.x86_64-linux.default
    ];
  };
}
```

The module installs `agent-toolbox` and `agent-toolbox-shell` and exposes the
materialized environment as the read-only
`config.programs.agentToolbox.environment`, the wrapper as
`config.programs.agentToolbox.wrapper` and the shell wrapper as
`config.programs.agentToolbox.shell`. Other modules can use those paths to give
a sandbox or a harness the same closure. The repository stays a composition root:
it does not depend on the sibling tool flakes, and harness wiring stays in the
host because NixOS rejects references to options no module declares.

## Integrating with the harnesses

```nix
{ config, ... }:
{
  # OpenCode V2: pinned tools for the terminal and shell tool.
  programs.coding-agents.opencode.settings = {
    shell = "${config.programs.agentToolbox.shell}/bin/agent-toolbox-shell";
  };

  # Codex: no custom shell; prepend the toolbox to the spawned-command PATH.
  programs.coding-agents.codex.settings.shell_environment_policy.set.PATH =
    "${config.programs.agentToolbox.environment}/bin:/run/current-system/sw/bin:/run/wrappers/bin:/usr/bin:/bin";
}
```

- **Shell route (always on):** point a harness shell setting at the toolbox
  shell, or add the environment's `bin` to the harness `PATH`. Every shell call
  then sees the full pinned toolset with one stable command prefix.
- **Sandbox route:** pass `config.programs.agentToolbox.environment` to
  `liteRuntime.extraPackages`, or bind `<environment>/bin` into the sandbox.
- **Diagnostics route:** OpenCode V2 accepts `lsp` configuration but does not
  run language servers or produce LSP diagnostics. Use the project's compiler,
  typecheck and lint commands through the toolbox, as with Codex. The `lsp`
  group remains available for clients that actually start language servers.
  See [`docs/lsp.md`](docs/lsp.md).
- **MCP route (optional, single tool):** see [`integration.md`](integration.md).
- **Sibling tools:** add `project-check`, `ast-index`, `agent-security-scan` or the research client via
  `extraPackages`; the repository's `.project-checks.json` then resolves its
  `requires` from the toolbox `PATH`. See [`project-check.md`](project-check.md).

Per-project shells, `nix develop -c`, `print-dev-env`, direnv pitfalls and the
manager comparison are in [`shells.md`](shells.md).

## Checks

```sh
nix flake check        # evaluates groups, module options and the wrapper
nix fmt                # nixfmt-tree
project-check fast     # the same gate through the shared runner
```

## Scope

`x86_64-linux`, pinned Nixpkgs, English source and documentation. No credentials,
personal paths or host identity belong in this repository.
