# Architecture

The repository has three layers, each independently testable:

1. **Tool groups** (`nix/tool-groups.nix`) — plain package lists selected by
   name. No shell, no hook, no policy.
2. **Surfaces** (`nix/shells.nix`, `nix/toolbox.nix`) — dev shells for humans and
   the single-argv toolbox for agents.
3. **Host integration** (`nix/module.nix`) — a NixOS module that installs the
   wrapper and exposes its environment to other modules.

Nothing in these layers grants authority. They compose `PATH`; the sandbox,
network policy, credentials and approvals belong to `lite-runtime-nix`,
`agent-runtime-nix` or the host.

## ADR-001 — Aggregate tools in this repository instead of per project

Context: every project otherwise repeats a tool list, and each list drifts.

Decision: one pinned composition root defines groups of tools; projects select
groups or their own `nix develop`, and the host selects groups for the agent.

Consequence: one place to review versions and one closure to cache. A project
with special needs keeps its own flake; the toolbox is a baseline, not a
replacement.

## ADR-002 — One stable argv instead of one tool per executable

Context: provider prompt caches are built over the prefix `tools → system →
messages`. Anthropic: "Modifying tool definitions (names, descriptions,
parameters) invalidates the entire cache." OpenAI: tool names, descriptions,
schemas and **ordering** participate in the cached prefix. The MCP specification
(2026-07-28) requires deterministic tool ordering so clients can cache the tool
list and keep prompt caches stable.

Decision: expose the whole toolset through one program, `agent-toolbox <argv>`,
and, when an MCP surface is wanted, through **one** MCP tool that takes an argv.
Do not expose one MCP tool per executable.

Consequence: the tool definition and the agent's command prefix stay byte-stable
across sessions and sessions stay cache-friendly. The tradeoff is a slightly
longer argv per call and no per-tool schema help; `agent-toolbox --list` and the
group docs cover discovery.

## ADR-003 — argv only, never a shell string

Context: shell-string execution is the recurring command-injection defect in
agent tool servers; the private `project-check` runner and the architecture kit
already standardize on argv arrays.

Decision: the wrapper executes an argv array with `exec "$@"`; it never
interpolates user input into a shell. Command discovery is a fixed environment,
not a `PATH` lookup outside it.

Consequence: the wrapper cannot express pipes, redirects or `&&` chains. Agents
run a small number of argv calls, or use an allowed shell explicitly
(`agent-toolbox bash -c '...'`) when they accept that risk inside the existing
boundary.

## ADR-004 — Groups, not one giant closure

Context: the full toolset (compilers, language runtimes, LSP servers, scanners)
is large; constrained hosts and CI do not need all of it.

Decision: named groups plus two unions, `agent` (all) and `light` (core, git,
search, nix, runtime). The module selects groups per host.

Consequence: closure size is a configuration decision. A host that only needs
search and git does not pull Rust or Node.

## ADR-005 — Stay a composition root

Context: the sibling private tools (`ast-index`, `project-check`,
`research-client`) are separate flakes with their own pins and tests.

Decision: this repository does not depend on them. A host passes their packages
through `programs.agentToolbox.extraPackages`; a project adds them to its own
shell.

Consequence: no cross-repository lockstep, no private input in a shared flake.
The cost is one line of host configuration per sibling tool.

## ADR-007 — Leave harness wiring to the host

Context: a soft integration would set `programs.coding-agents.*` when the
harness module is present. NixOS rejects a reference to an option that no module
declares, even under `lib.mkIf false`, so option detection cannot guard the
assignment safely.

Decision: expose `environment`, `wrapper` and `shell` as read-only values and
document the two assignments the host makes (OpenCode `shell`/`lsp`, Codex
`shell_environment_policy.set.PATH`).

Consequence: no hidden coupling and no fragile detection. The cost is two lines
of host configuration, which is the correct place for a composition decision.

## ADR-006 — Prefer harness-native LSP over per-language MCP tools

Context: language intelligence is the largest capability gap, and every
LSP→MCP bridge found exposes many tools per language. Anthropic documents that
modifying tool definitions invalidates the entire prompt cache; harness-native
LSP exposes one tool with operations, so adding a language changes configuration,
not the tool surface.

Decision (corrected 2026-09-20): ship pinned language servers in the `lsp` group
for clients that run them. OpenCode V2 preserves LSP configuration but does not
run servers or expose diagnostics; the original V1-based assumption above is
superseded by the V2 migration guide. For both current OpenCode and Codex wiring,
prefer project-declared CLI diagnostics (`basedpyright --outputjson`, `ruff`,
`tsc --noEmit`, `cargo check`) over adding an MCP tool per language.

Consequence: installed binaries are not evidence of native LSP integration.
CLI diagnostics and the optional AST index provide the supported feedback and
navigation paths. See [`lsp.md`](lsp.md).

## Open questions

- **MCP surface.** A single `toolbox_exec` MCP tool is designed but not yet
  implemented. See `docs/integration.md`.
- **Project dev shell composition.** Whether the wrapper should merge a project's
  own `nix develop` environment with the baseline, or keep them separate. The
  current answer is separate: baseline for shell commands, project shell via
  `nix develop -c` for project-specific commands (see `docs/shells.md`).
