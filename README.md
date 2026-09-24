# public-harness-tools

Free, public building blocks for coding-agent harnesses: an allowlisted skill
catalog and deterministic mirrors of selected tool repositories.

Every artifact here is exported from a private source through an explicit
allowlist. The exporters read only committed Git content, never copy build
output or credentials, and refuse to write a mirror when the finished content
still contains forbidden names, credential patterns, operator paths or
unexpected email domains.

## Skills

`skills/` is the public catalog. Each skill is one directory with a `SKILL.md`,
an optional `agents/openai.yaml`, and optional `references/`, `scripts/` or
`assets/` resources.

```sh
python3 scripts/validate_catalog.py
sh -n skills/test-and-regression/scripts/regression-gate.sh
python3 -m unittest discover -s tests -v
```

`scripts/export_public_skills.py <new.tar.gz>` builds the deterministic
allowlist-only archive of the catalog.

## Tools

`tools/<name>/` contains mirrored tool repositories. Each mirror is exported
from Git-tracked files at an exact revision, then verified and recorded in
[`tools/manifest.json`](tools/manifest.json) with its upstream repository,
revision, file count and SHA-256 content digest. Every mirrored repository keeps
its own upstream license.

| Tool | Purpose |
| --- | --- |
| [project-check-nix](tools/project-check-nix) | Portable, argv-only project verification runner driven by a per-repository manifest. |
| [repo-scaffold-nix](tools/repo-scaffold-nix) | Fail-closed scaffolder and flake templates for the files every repository should carry. |
| [agent-toolbox-nix](tools/agent-toolbox-nix) | Pinned, modular tool environment and single-argv toolbox for coding agents. |
| [ast-index-nix](tools/ast-index-nix) | Local-first AST code index and query service for agent harnesses. |

Export a new mirror, or verify the existing ones:

```sh
python3 scripts/export_public_tools.py --source /path/to/private-repo --name repo-name
python3 scripts/export_public_tools.py --verify
```

The reviewed replacement and forbidden-content policy is
[`scripts/public_tool_rules.json`](scripts/public_tool_rules.json). A mirror is
published only when its verification passes; the manifest digest makes later
drift detectable.

### Using a mirrored tool

Mirrors are ordinary repositories that live inside this monorepo. Point a Nix
flake input at the tool directory:

```nix
inputs.project-check.url = "git+https://github.com/timfewi/public-harness-tools?dir=tools/project-check-nix";
```

Or clone this repository and use the tool directory directly.
