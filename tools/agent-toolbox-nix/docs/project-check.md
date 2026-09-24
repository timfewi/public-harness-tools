# project-check and the toolbox

`project-check` and `agent-toolbox` are orthogonal and compose:

- **agent-toolbox** supplies pinned executables on `PATH`.
- **project-check** is one of those executables and consumes exactly that
  `PATH`: every check in `.project-checks.json` declares the programs it needs
  (`requires`), and `project-check` resolves them with `shutil.which`.

So the toolbox answers "are the tools present?" and `project-check` answers
"does the repository pass its declared checks?" Neither knows the other
internally; the host puts `project-check` into the toolbox environment.

## Division of responsibility

| Owner | Responsibility |
| --- | --- |
| Repository | `.project-checks.json`: names, argv, `cwd`, `requires`, timeout, profiles |
| `project-check` | argv-only execution, timeout + process-group kill, scratch dirs, coverage/blocked/failed report, exit status |
| `agent-toolbox` | guarantees the `requires` commands exist, and exposes `project-check` as one stable argv |
| `lite-runtime-nix` | the boundary (filesystem, credentials) around both |

## What project-check needs from PATH

The packaged runner bakes in its own Python, the pinned Semgrep scanner, the CA
bundle and the immutable quality rules as store paths, so **`baseline` works
without a toolbox**. Everything a project declares in its manifest is resolved
from `PATH`:

```jsonc
{
  "version": 1,
  "checks": [
    {
      "name": "lint",
      "argv": ["statix", "check", "."],
      "requires": ["statix"],
      "timeout_seconds": 120,
      "profiles": ["fast"]
    }
  ]
}
```

If a required program is missing, the check reports `blocked`, not `failed`.
A toolbox environment makes `blocked` the exception instead of the norm.

## Wiring

Add the runner to the toolbox environment and use the single wrapper:

```nix
programs.agentToolbox.extraPackages = [
  project-check.packages.x86_64-linux.project-check
];
```

```sh
agent-toolbox project-check fast
agent-toolbox project-check full --json
```

`project-check` inherits the toolbox `PATH`, so `requires` are satisfied by the
same pinned closure the rest of the agent's commands use.

## This repository as an example

[`../.project-checks.json`](../.project-checks.json) declares `nix`, `statix` and
`deadnix`; the `nix` group of the toolbox provides all three. Together with
`checks.lint`, the repository lints itself through both paths.

## Caveats

- **Do not use `watch` for agent work.** It polls (0.2 s) and runs until
  interrupted; a tool call would never return. Use `fast`, `full` or `--json`.
- **`blocked` is not `failed`.** A missing tool or a detected environment
  failure (`no matching package named`, `required command not found`,
  `TOOLCHAIN_*`) is `blocked`; a nonzero check is `failed`. Report them
  differently.
- **Warnings fail a passed check.** `project-check` treats warning output from a
  successful check as unsuccessful.
- **`requires` matches names, not paths.** The toolbox must provide the command
  name, not only a store path.
- **`project-check` sets `NIX_SSL_CERT_FILE` and `SSL_CERT_FILE`** to the baked
  CA bundle; do not override them in the environment.
- **Baseline covers Python only.** Other languages must be covered by the
  project's own checks.
- **Not a sandbox.** It runs argv in the current environment; `nix`-based checks
  may still need the network. Use the sandbox route for a real boundary.
