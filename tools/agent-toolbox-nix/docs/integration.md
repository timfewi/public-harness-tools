# Harness integration

The toolbox is a `PATH` provider. This repository exposes the values; the host
wires them where the harness options live. That boundary is deliberate: NixOS
rejects a reference to an option that no module declares, so a toolbox module
cannot safely assign `programs.coding-agents.*` on a host that does not import
the harness flake. See the wiring samples below.

## Shell route (always on)

Give the agent's shell tool the toolbox `PATH` by pointing the harness shell
setting at the exported shell wrapper, or by prepending the environment's `bin`.

```sh
agent-toolbox rg -n 'needle' src     # stable single argv
agent-toolbox --list                 # every command
agent-toolbox --env                  # the environment store path
```

This route adds no MCP tool, so nothing is added to the model-visible tool list
and no prompt cache is affected.

## OpenCode

In OpenCode V2, `shell` names a shell binary used for the terminal and shell
tools. Point it at the toolbox shell. V2 does not run language servers; use
project-declared CLI diagnostics instead of treating `lsp = true` as integration.

```nix
{ config, ... }:
{
  programs.coding-agents.opencode.settings = {
    shell = "${config.programs.agentToolbox.shell}/bin/agent-toolbox-shell";
  };
}
```

`agent-toolbox-shell` is a bash-compatible wrapper: it fixes `PATH` and then
`exec bash "$@"`, so OpenCode's implied `<shell> -c "<command>"` works. Host
`opencode.settings` still override these values.

## Codex

Codex has no custom-shell option; it exposes `[shell_environment_policy]`.
Prepend the toolbox environment to `PATH`. Keep the system path so helpers such
as `ssh`, `less` and the Nix client stay reachable.

```nix
{ config, lib, ... }:
{
  programs.coding-agents.codex.settings.shell_environment_policy.set.PATH =
    "${config.programs.agentToolbox.environment}/bin:/run/current-system/sw/bin:/run/wrappers/bin:/usr/bin:/bin";
}
```

`set.PATH` is a literal value, not an expansion of the runtime `$PATH`, so it
must list the fallback directories explicitly. `features.shell_snapshot`
(default on) snapshots `PATH` at startup, which is why the value is fixed at
configuration time.

## Sandbox route

For a real boundary, pass the environment to a sandbox module, for example
`lite-runtime-nix`:

```nix
liteRuntime.extraPackages = [ config.programs.agentToolbox.environment ];
```

The sandbox still owns network, filesystem and credential policy. The toolbox
only decides which executables exist.

## MCP route (optional, single tool)

Some harnesses reach tools only through MCP. The design is one tool, not one per
executable, to keep the model-visible surface small and cache-stable:

```jsonc
// tool: toolbox_exec
{
  "argv": ["rg", "-n", "needle", "src"],   // argv[0] is the executable
  "cwd": "."                               // optional, workspace-relative
}
```

Rules the implementation must keep:

- execute the argv array directly, never through a shell;
- reject empty argv and resolve `argv[0]` only inside the toolbox environment;
- bound stdout/stderr and wall time, and report truncation;
- mark the tool read-only only when the command allow-list makes that true.

A single-tool MCP server is **not implemented yet**. Until it is, use the shell
route. If it is added, register it exactly once and never add or remove tools
mid-session: Anthropic documents that modifying tool definitions invalidates the
entire cache, and the MCP specification requires deterministic tool ordering for
the same reason.

## Registering sibling tools

`ast-index`, `project-check` and the research client are separate repositories.
Add them at the host:

```nix
programs.agentToolbox.extraPackages = [
  ast-index.packages.x86_64-linux.ast-index
  project-check.packages.x86_64-linux.project-check
];
```

Then the agent reaches them through the same stable program name:

```sh
agent-toolbox ast-index status
agent-toolbox project-check fast
agent-toolbox project-check full --json
```

`project-check` is particularly complementary: it resolves every `requires`
entry of `.project-checks.json` from the toolbox `PATH`, so the toolbox decides
tool availability and the repository decides its checks. See
[`project-check.md`](project-check.md) for the contract and caveats.

Do not add a dependency from this flake to a private sibling; that would put a
private input into every consumer's lockfile.
