# Tool groups

Groups are defined in [`nix/tool-groups.nix`](../nix/tool-groups.nix). Each group
is an independent package list; selecting a group only adds executables to
`PATH`. `commands` names one representative command per group and is checked by
the module test.

| Group | Representative commands | Purpose |
| --- | --- | --- |
| `core` | `rg`, `fd`, `jq`, `ls`, `sed`, `tree` | POSIX and search basics |
| `git` | `git`, `gh`, `delta`, `git-lfs` | version control and review |
| `nix` | `nix`, `nixfmt`, `statix`, `deadnix` | Nix edit, format, lint |
| `search` | `rg`, `ast-grep`, `tree-sitter`, `ctags`, `hyperfine`, `tokei` | structural and measured search |
| `rust` | `cargo`, `rustc`, `rust-analyzer`, `rustfmt`, `cargo-nextest`, `sqlite3` | Rust toolchain |
| `node` | `node`, `bun`, `pnpm`, `tsc` | JavaScript/TypeScript runtimes |
| `python` | `python3`, `uv`, `ruff`, `basedpyright` | Python toolchain |
| `go` | `go`, `gopls` | Go toolchain |
| `c` | `gcc`, `clang`, `cmake`, `make`, `ninja`, `valgrind` | native toolchain |
| `lsp` | `rust-analyzer`, `typescript-language-server`, `basedpyright`, `nixd`, `nil`, `gopls`, `taplo` | language servers |
| `lint` | `shellcheck`, `luacheck`, `ruff`, `eslint`, `prettier`, `biome`, `yamllint`, `hadolint`, `actionlint`, `semgrep`, `gitleaks` | format and lint |
| `wasm` | `wasmtime`, `wasm-tools`, `wit-bindgen` | WebAssembly tooling |
| `proto` | `protoc`, `buf`, `grpcurl` | protobuf tooling |
| `runtime` | `bwrap`, `flock`, `just` | sandbox and task helpers |

## Unions

| Set | Definition |
| --- | --- |
| `agent` | every group above (`lib.unique` union) |
| `light` | `core` + `git` + `search` + `nix` + `runtime` |

An empty `programs.agentToolbox.groups` selects `agent`.

## Adding a tool

1. Add the package to exactly one group.
2. If it is representative, add its command to `commands.<group>`.
3. Run `nix flake check`; the module test asserts every group is nonempty and
   every group has at least one documented command.

Prefer an existing group over a new one. A new group needs a reason in
[`architecture.md`](architecture.md).
