{
  self,
  nixpkgs,
  system,
}:
let
  pkgs = nixpkgs.legacyPackages.${system};
  groups = import ../nix/tool-groups.nix { inherit pkgs; };
  evaluate =
    options:
    (nixpkgs.lib.nixosSystem {
      inherit system;
      modules = [
        self.nixosModules.default
        {
          system.stateVersion = "26.05";
          boot.isContainer = true;
        }
        options
      ];
    }).config;
  enabled = evaluate { programs.agentToolbox.enable = true; };
  disabled = evaluate { };
  selected = evaluate {
    programs.agentToolbox = {
      enable = true;
      groups = [
        "core"
        "git"
        "lsp"
      ];
    };
  };
  withExtra = evaluate {
    programs.agentToolbox = {
      enable = true;
      groups = [ "core" ];
      extraPackages = [ pkgs.hello ];
    };
  };
  wrapper = self.packages.${system}.agent-toolbox;
  fixtureTool = pkgs.writeShellApplication {
    name = "judgment-fixture";
    text = ''
      printf '%s\n' "$1"
      exit "$2"
    '';
  };
  judgmentToolbox = (import ../nix/toolbox.nix { inherit pkgs groups; }).mkToolbox [
    pkgs.python3
    fixtureTool
  ];
  lintSource = nixpkgs.lib.fileset.toSource {
    root = ../.;
    fileset = nixpkgs.lib.fileset.unions [
      ../flake.nix
      ../nix
      ../tests
    ];
  };
in
assert builtins.length groups.sets.agent > 80;
assert builtins.all (name: groups.sets.${name} != [ ]) groups.names;
assert builtins.all (name: (groups.commands.${name} or [ ]) != [ ]) groups.names;
assert builtins.elem pkgs.ripgrep groups.sets.core;
assert builtins.elem pkgs.rust-analyzer groups.sets.lsp;
# An empty group list selects the agent union.
assert nixpkgs.lib.isDerivation enabled.programs.agentToolbox.environment;
assert nixpkgs.lib.isDerivation selected.programs.agentToolbox.environment;
assert nixpkgs.lib.isDerivation withExtra.programs.agentToolbox.environment;
assert builtins.elem wrapper enabled.environment.systemPackages;
# The module wrapper is byte-identical to the flake package for the agent union.
assert enabled.programs.agentToolbox.wrapper == wrapper;
assert !(builtins.elem wrapper disabled.environment.systemPackages);
# Selecting fewer groups yields a different environment than the union.
assert selected.programs.agentToolbox.environment != enabled.programs.agentToolbox.environment;
# The disabled module installs no wrapper and no environment file.
assert !(disabled.environment.etc ? "agent-toolbox/env");
# The module exposes the environment, the wrapper and the shell.
assert nixpkgs.lib.isDerivation enabled.programs.agentToolbox.shell;
assert enabled.programs.agentToolbox.shell != enabled.programs.agentToolbox.wrapper;
{
  judgment-tools =
    pkgs.runCommand "agent-toolbox-judgment-tools"
      {
        nativeBuildInputs = [ pkgs.python3 ];
      }
      ''
        python3 - <<'PY'
        import subprocess
        command = ["${judgmentToolbox}/bin/agent-toolbox"]
        subprocess.run(command + ["python3", "-c", "import json; assert json.loads('true') is True"], check=True)
        argument = "literal ; $(must-not-execute)"
        result = subprocess.run(command + ["judgment-fixture", argument, "7"], capture_output=True, text=True)
        assert result.stdout == argument + "\n", result
        assert result.returncode == 7, result
        PY
        touch "$out"
      '';
  module-eval = pkgs.runCommand "agent-toolbox-eval-check" { } "touch $out";
  # Deterministic lint gate: deadnix for dead code, statix for anti-patterns.
  lint =
    pkgs.runCommand "agent-toolbox-lint"
      {
        nativeBuildInputs = [
          pkgs.statix
          pkgs.deadnix
        ];
      }
      ''
        cd ${lintSource}
        statix check .
        deadnix --fail .
        touch $out
      '';
}
