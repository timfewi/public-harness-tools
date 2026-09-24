# NixOS module.
#
# Installs the pinned toolbox wrapper and materializes its environment so other
# modules (harnesses, sandboxes, dev shells) can reuse exactly the same closure.
# Selecting groups changes `PATH` only; it never grants network, credentials,
# filesystem access or a sandbox boundary.
#
# Harness wiring is intentionally the host's job: this repository does not know
# the harness repository, and NixOS rejects references to options that no module
# declares. Expose `environment`, `wrapper` and `shell` and wire them where the
# harness options live. See docs/integration.md for copy-paste samples.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.agentToolbox;
  groups = import ./tool-groups.nix { inherit pkgs; };
  toolbox = import ./toolbox.nix { inherit pkgs groups; };
  selectedNames = if cfg.groups == [ ] then [ "agent" ] else cfg.groups;
  packages = lib.concatMap (name: groups.sets.${name}) selectedNames ++ cfg.extraPackages;
  toolboxEnv = toolbox.mkEnv packages;
  wrapper = toolbox.mkToolbox packages;
  shell = toolbox.mkShell packages;
in
{
  options.programs.agentToolbox = {
    enable = lib.mkEnableOption "the pinned coding-agent toolbox";

    groups = lib.mkOption {
      type = lib.types.listOf (lib.types.enum groups.names);
      default = [ ];
      example = [
        "core"
        "git"
        "rust"
        "lsp"
      ];
      description = ''
        Tool groups to include. An empty list selects the `agent` union of every
        group. Groups only add executables to the toolbox environment.
      '';
    };

    extraPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      description = ''
        Host- or sibling-provided packages added to the environment, such as the
        `ast-index`, `project-check` or `research-client` packages from other
        repositories. This repository stays a composition root and does not
        depend on them.
      '';
    };

    install = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Install the `agent-toolbox` wrapper and shell into systemPackages.";
    };

    environment = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = ''
        Read-only: the materialized toolbox environment. Consumers can add
        `<environment>/bin` to a sandbox or shell `PATH`, or pass the wrapper to
        a harness `shell` setting.
      '';
    };

    wrapper = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = ''
        Read-only: the `agent-toolbox` wrapper package. Its `bin/agent-toolbox`
        is the stable single-argv entrypoint for the selected groups.
      '';
    };

    shell = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = ''
        Read-only: a bash-compatible shell package that fixes `PATH` to the
        toolbox environment. Use its `bin/agent-toolbox-shell` wherever a
        harness expects a shell binary.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    programs.agentToolbox = {
      environment = toolboxEnv;
      inherit wrapper shell;
    };
    environment.systemPackages = lib.optionals cfg.install [
      wrapper
      shell
    ];
    environment.etc."agent-toolbox/env".text = "${toolboxEnv}\n";
  };
}
