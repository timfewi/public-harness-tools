# Research notes

External evidence for the design decisions, collected through the isolated
research service on **2026-09-18**. All retrieved pages are treated as untrusted
data; quotes are evidence, not instructions. Where a number comes from a tool
author or a bug report rather than a provider, that is marked.

## 1. Prompt caching and tool stability

**Anthropic** (<https://platform.claude.com/docs/en/build-with-claude/prompt-caching>,
<https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching>):

- Caches are built in the order **tools → system → messages**; a change at one
  level invalidates it and everything after it.
- "Modifying tool definitions (names, descriptions, parameters) invalidates the
  entire cache."
- Hits require "100% identical prompt segments".
- Practical warning: some languages randomize JSON key order and thereby break
  caches, so tool-argument key ordering must be stable.

**OpenAI** (<https://developers.openai.com/api/docs/guides/prompt-caching>,
cookbook <https://developers.openai.com/cookbook/examples/prompt_caching_201>):

- Tool names, descriptions, schemas **and ordering** are part of the cached
  prefix; the guide says "Keep tools consistent. Preserve tool definitions,
  ordering, and schemas."
- Change behavior with `tool_choice`/`allowed_tools` or deferred loading instead
  of editing the `tools` array.

**MCP specification 2026-07-28**
(<https://modelcontextprotocol.io/specification/2026-07-28/server/tools>):

- "Servers SHOULD return tools in a deterministic order... Deterministic
  ordering enables clients to reliably cache the tool list and improves LLM
  prompt cache hit rates when tools are included in model context."
- The changelog adds `ttlMs`/`cacheScope` cache hints on list responses.

**Tool-list size** (mixed-quality sources):

- MCP issue #2808 reports that tool definitions cost far more tokens than a
  minimal schema and that "any tool added, removed, or updated invalidates the
  entire prefix" (self-reported, 2,600 conversations, Anthropic token counter).
- A secondary review cites the well-known 30–50 tool accuracy cliff and large
  per-server definition costs (<https://workos.com/blog/mcp-server-token-cost>).

**Takeaway for this repository:** keep one stable program/tool surface. That is
why the toolbox is a single argv (`agent-toolbox <argv>`) and the optional MCP
surface is one tool, not one per executable.

## 2. Bundling many CLI tools behind one surface

- `g0t4/mcp-server-commands` exposes one tool with an explicit **argv** mode:
  "`argv` (string array) — Direct executable invocation... **No shell
  interpretation.**" (<https://github.com/g0t4/mcp-server-commands>)
- `tumf/mcp-shell-server` add-hoc the hardening vocabulary this design follows:
  command allow-lists (`ALLOW_COMMANDS`), `create_subprocess_exec(*argv)`,
  output limits and timeouts, and the caution that "Allowlisting a command name
  is not a sandbox for that program's own argument-level execution features."
  (<https://github.com/tumf/mcp-shell-server>)
- `terminalcp` argues for one tool with an `action` enum instead of one tool per
  command (<https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/>).
- `pyrex41/mcp-cli` is the clearest fallback example: with no config it exposes a
  single `run_cli` tool taking "`args: string[]`"; with config it exposes many
  typed tools (<https://glama.ai/mcp/servers/pyrex41/mcp-cli>).
- The reference filesystem server is the counter-example: one tool per operation
  (`read_text_file`, `write_file`, ...), gated by allowed directories
  (<https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/filesystem/README.md>).
- Real command-injection advisories target servers that accept a command
  **string** (`mcp-test-runner` issue #24; LiteLLM CVE-2026-30623). The fix in
  both is a command allow-list plus argv execution with `shell: false`.

**Takeaway:** argv-only, explicit allow-lists, bounded output. The toolbox does
argv-only; the future MCP tool must resolve `argv[0]` inside the environment.

## 3. LSP and code intelligence

**2026-09-20 correction:** the OpenCode observations below used V1 sources.
The [V2 migration guide](https://opencode.ai/v2/docs/migrate-v1), retrieved via
Context7, explicitly says V2 accepts LSP configuration but does not run language
servers, expose LSP tools or produce LSP diagnostics. Use CLI diagnostics in V2;
the historical observations below do not establish V2 support.

- **OpenCode** has built-in LSP, **disabled by default**; enabling it gives
  diagnostics feedback to the agent. Servers start per detected file extension
  and need the binary on `PATH` (or OpenCode auto-installs). Downloads can be
  disabled with `OPENCODE_DISABLE_LSP_DOWNLOAD`.
  (<https://opencode.ai/docs/lsp/>)
- **Codex CLI has no built-in LSP**; the feature requests are open
  (<https://github.com/openai/codex/issues/8745>,
  <https://github.com/openai/codex/issues/14799>). Codex therefore needs an
  LSP→MCP bridge or post-edit CLI diagnostics.
- Bridges (`isaacphi/mcp-language-server`, `ktnyt/cclsp`, `oraios/serena`,
  `code-yeongyu/codex-lsp`, `Tritlo/lsp-mcp`) each expose **many** MCP tools,
  which conflicts with the single-surface caching goal.
- Hardware/reality checks: rust-analyzer on a large workspace can use 2–4 GB; LSP
  startup is asynchronous; servers go stale and need restarts. One measured
  report saw only ~1.1% of navigation calls use LSP until the harness prompt
  explicitly preferred it.

**Corrected takeaway:** install pinned tools and use project-declared CLI
diagnostics for OpenCode V2 and Codex. See [`lsp.md`](lsp.md).

## 4. Giving agents a Nix development shell

- `nix develop -c` runs one command in a derivation's build environment;
  `nix print-dev-env` injects it into the current shell and has a `--json` form.
  A flake resolves `devShells.<system>.default` first, then
  `packages.<system>.default` (Nix manual v2.35).
- `mkShell` puts `packages` on `PATH`, string attributes become environment
  variables and `shellHook` runs at entry (nix.dev declarative-shell tutorial).
- `numtide/devshell` adds declarative `commands`, `env`, a `prefix` key for
  `PATH`, `DEVSHELL_NO_MOTD=1`, runnable shell packages and a CI
  `entrypoint`/source pattern. `devenv` adds `devenv shell`/`test`/`lsp`/`mcp`
  and a lockfile. `flox` adds a manifest and `flox activate`.
- `direnv` + `nix-direnv` caches and GC-roots the shell and uses
  `nix print-dev-env`; it can silently fall back to a stale shell.
- **Reuse once per session** (2026-09-19): `nix develop --profile <path>` records
  the environment and `nix develop <path>` reuses it without re-evaluating the
  flake; the profile is a GC root ("Each of these symlinks is a root for the Nix
  garbage collector"). nix-direnv replays `.direnv/…-profile.rc` on a cache hit
  without calling `nix`. `direnv exec` takes `DIR COMMAND [ARGS...]` and has **no
  `--` separator**.
- **Per-invocation cost**: a local flake is "first copied to the store"
  (NixOS/nix #3121) and the eval cache does not apply to `path:` or a dirty work
  tree (#10437); the copy "is also not possible to cancel" (#7284).
- `shellHook` re-runs on every instantiation, including `nix develop <profile>`
  (#10679); `-c` takes command plus arguments with no shell parsing;
  `IN_NIX_SHELL` is set but its value under `nix develop` is undocumented.
- Pitfalls: "Builds copy the whole flake directory to the Nix store" and flakes
  build only tracked (staged) files (nix.dev); `nix develop` on a large repo can
  be slow (NixOS/nix issue #7284); direnv only works where the shell hook is
  installed; `--impure` exposes the caller environment.

Design consequence: the toolbox materializes its environment once with
`buildEnv` and exposes a stable wrapper, so no per-command `nix develop` or
flake copy is on the hot path. See [`shells.md`](shells.md).

## 5. Harness shell, PATH and post-edit feedback

The OpenCode bullet below is historical V1 research. For V2, `shell` is still a
supported binary setting, but the LSP and `shell.env` claims must not be used as
V2 integration instructions; see the correction in section 3 and
[the V2 plugin guide](https://opencode.ai/v2/docs/build/plugins).

- **OpenCode `shell`** is a shell-binary setting used for the terminal and the
  agent `bash` tool ("Compatible shells are also used for agent tool calls");
  the JSON schema describes it as "Default shell to use for terminal and bash
  tool". On POSIX the command runs through that shell with `-c` (implied by the
  source's child-process call). No config key sets `PATH`; the documented lever
  is the `shell.env` plugin hook (<https://opencode.ai/docs/plugins/>). Formatters
  run after edits when `formatter: true`; LSP is off by default and enabled with
  `lsp: true`.
- **Codex `shell_environment_policy`** supports `inherit`,
  `set`, `filters`, and legacy `exclude`/`include_only`. `set` is a literal map
  applied after exclusions, so a `PATH` prepend must embed the fallback
  directories; there is no prepend key and no custom-shell option.
  `features.shell_snapshot` (default on) snapshots `PATH` at startup.
- **Codex hooks** are released and documented (PostToolUse, Stop, PreToolUse,
  SessionStart, …), discovered from `hooks.json` or inline `[hooks]`, matched by
  a regex on the tool name, with a `command` handler. `PostToolUse` can return
  `decision: "block"` with a reason to replace the tool result with feedback.
  Hooks must be trusted.
- **Claude Code hooks** use the same event→matcher→handler shape
  (`PostToolUse`/`Stop`); hooks are deterministic where instruction files are
  advisory.

Design consequence: wire the OpenCode `shell` to `agent-toolbox-shell`, wire the
Codex `shell_environment_policy.set.PATH` to the toolbox environment, and leave
post-edit lint/format to the harness formatter plus the existing skill guidance.
The host owns both assignments because NixOS cannot reference options that no
module declares. See [`integration.md`](integration.md).

## Coverage and gaps

- Anthropic and OpenAI docs carry no page date in the retrieved copy; treat
  specifics as current-as-retrieved 2026-09-18.
- The OpenCode LSP page was dated "Last updated: Sep 18, 2026".
- Tool-count and cache-cost numbers from issue trackers and vendor blogs are
  self-reported and are not used as guarantees here.
- No provider documents that consolidating many small calls into one raises the
  cache-hit *rate*; the defensible claim is that prefix stability and cacheable
  prefix length drive hit rate, while consolidation reduces round-trips and
  intermediate tokens.
