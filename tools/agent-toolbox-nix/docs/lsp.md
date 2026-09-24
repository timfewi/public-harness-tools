# LSP and code intelligence

The `lsp` group installs pinned language servers on `PATH`. That is necessary
but not sufficient: a harness still has to start them, pick a project root and
feed diagnostics back to the model. The routes differ by harness.

## What the environment provides

`rust-analyzer`, `typescript-language-server`, `basedpyright`, `nixd`, `nil`,
`gopls`, `taplo`, `yaml-language-server`, `bash-language-server`,
`lua-language-server`, `clangd` (`clang-tools`) and the VS Code language servers
(`vscode-langservers-extracted`).

## OpenCode V2

The V2 migration guide states that V2 accepts and preserves `lsp` configuration,
but does not run language servers, expose LSP tools or produce LSP diagnostics.
The earlier guidance here used V1 documentation and did not apply to the
installed V2 harness. Setting `lsp = true` is not an operational integration.

Point the harness shell at `agent-toolbox-shell` and use the project's declared
compiler, typecheck or lint checks. Examples include `cargo check`,
`basedpyright --outputjson`, `ruff check` and `tsc --noEmit`; use the repository's
own flags and scope. Structural navigation is separately available through
`ast-index` when the host registers it. See [integration.md](integration.md).

## Codex

Codex CLI has **no built-in LSP** as of the tracked feature requests
([#8745](https://github.com/openai/codex/issues/8745),
[#14799](https://github.com/openai/codex/issues/14799), both open). Two routes:

1. **CLI diagnostics through the toolbox (default).** Run the language's own
   checker after an edit: `basedpyright --outputjson .`, `ruff check`,
   `tsc --noEmit`, `cargo check`, `nix flake check`. This needs no extra tool
   surface and keeps the prompt cache stable.
2. **An LSP→MCP bridge (optional).** Bridges exist
   ([mcp-language-server](https://github.com/isaacphi/mcp-language-server),
   [cclsp](https://github.com/ktnyt/cclsp),
   [Serena](https://github.com/oraios/serena),
   [codex-lsp](https://github.com/code-yeongyu/codex-lsp)), but each exposes
   many MCP tools per language. Adding them changes the model-visible tool list
   and invalidates the prompt cache, which this repository exists to avoid.
   Select one deliberately and register it once per session.

## Why not one tool per language here

Anthropic documents that modifying tool definitions invalidates the entire
cache, and the MCP specification requires deterministic tool ordering so clients
can cache the tool list. Use a native LSP route only when the installed harness
actually implements it. For OpenCode V2 and the current Codex integration,
prefer CLI diagnostics over adding new tools per language.

## LSP needs a project root

Every bridge takes an explicit workspace root (`--workspace`, `root_dir`,
`rootDir`, `rootPatterns`). Installing a server does not decide which project it
serves. Start one server per project root; for monorepos prefer a bridge that
supports per-workspace instances.

## Costs and failure modes

- **Memory:** "Running rust-analyzer on a large Rust workspace can easily use
  2–4 GB of RAM" (community article).
- **Startup:** servers initialize asynchronously; requests before initialization
  return nothing, so a first call may look broken.
- **Staleness:** servers can drift and need restarts; treat diagnostics as hints
  and confirm with a read.
- **Execution:** LSP servers run local code from the project. Keep them inside
  the same boundary as the rest of the agent (for example `lite-runtime-nix`).

## Evidence

Provider and project documentation read through the isolated research service
(2026-09-18):

- OpenCode V2 correction, checked through Context7 on 2026-09-20 —
  <https://opencode.ai/v2/docs/migrate-v1>
- OpenCode V2 shell configuration — <https://opencode.ai/v2/docs/config>
- Codex LSP feature requests — <https://github.com/openai/codex/issues/8745>,
  <https://github.com/openai/codex/issues/14799>
- mcp-language-server — <https://github.com/isaacphi/mcp-language-server>
- cclsp — <https://github.com/ktnyt/cclsp>
- Serena — <https://github.com/oraios/serena>
- codex-lsp — <https://github.com/code-yeongyu/codex-lsp>
- Claude Code LSP overview — <https://circleci.com/blog/claude-code-lsp/>
