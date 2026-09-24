# One devShell per tool group plus the `agent` and `light` unions.
#
# `nix develop` in a consuming repository should describe that repository's own
# toolchain. These shells are the shared baseline an agent can always fall back
# to; they select packages by group name and add no hooks, network access or
# credentials.
{ pkgs, groups }:
let
  mk =
    name: packages:
    pkgs.mkShell {
      name = "agent-toolbox-${name}";
      inherit packages;
      shellHook = ''
        echo "agent-toolbox: ${name} shell" >&2
      '';
    };
in
{
  default = mk "default" groups.sets.agent;
}
// pkgs.lib.genAttrs (builtins.attrNames groups.sets) (name: mk name groups.sets.${name})
