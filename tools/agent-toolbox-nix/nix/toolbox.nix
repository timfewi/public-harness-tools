# The single-argv toolbox.
#
# `agent-toolbox <argv...>` runs any pinned tool with the selected environment
# on `PATH`. The program name and its interface are stable, so an agent keeps
# one tool definition and one command prefix instead of learning one tool per
# executable. This mirrors the single-tool MCP design used by the sibling
# `ast-index` service and keeps prompt-cacheable prefixes stable.
{ pkgs, groups }:
let
  inherit (pkgs) lib;

  mkEnv =
    packages:
    pkgs.buildEnv {
      name = "agent-toolbox-env";
      paths = lib.unique packages;
      pathsToLink = [ "/bin" ];
    };

  mkToolbox =
    packages:
    pkgs.writeShellApplication {
      name = "agent-toolbox";
      runtimeInputs = [
        pkgs.coreutils
        pkgs.bashInteractive
      ];
      text = ''
        toolbox_env=${mkEnv packages}

        case "''${1-}" in
          --env)
            printf '%s\n' "$toolbox_env"
            exit 0
            ;;
          --list)
            for candidate in "$toolbox_env"/bin/*; do
              printf '%s\n' "''${candidate##*/}"
            done | sort -u
            exit 0
            ;;
        esac

        export PATH="$toolbox_env/bin:$PATH"

        if [ "$#" -eq 0 ]; then
          exec bash --noprofile --norc
        fi

        exec "$@"
      '';
    };

  # A bash-compatible shell that fixes PATH. OpenCode's `shell` setting names a
  # shell binary used for the terminal and the agent `bash` tool, so this script
  # accepts the same `-c <command>` arguments as bash.
  mkShell =
    packages:
    pkgs.writeShellApplication {
      name = "agent-toolbox-shell";
      runtimeInputs = [
        pkgs.coreutils
        pkgs.bashInteractive
      ];
      text = ''
        toolbox_env=${mkEnv packages}
        export PATH="$toolbox_env/bin:$PATH"
        exec bash "$@"
      '';
    };
in
{
  inherit mkEnv mkToolbox mkShell;
  env = mkEnv groups.sets.agent;
  default = mkToolbox groups.sets.agent;
}
