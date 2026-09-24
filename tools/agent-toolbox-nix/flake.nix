{
  description = "Pinned, modular tool environment and single-argv toolbox for coding agents";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/eaad089433ca2bb662274377d33df3d0e51ef28b";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      groups = import ./nix/tool-groups.nix { inherit pkgs; };
      toolbox = import ./nix/toolbox.nix { inherit pkgs groups; };
    in
    {
      packages.${system} = {
        inherit (toolbox) default;
        agent-toolbox = toolbox.default;
        # bash-compatible shell that fixes PATH to the same environment.
        agent-toolbox-shell = toolbox.mkShell groups.sets.agent;
        # Small fallback built from core, git, search, nix and runtime only.
        agent-toolbox-light = toolbox.mkToolbox groups.sets.light;
      };

      devShells.${system} = import ./nix/shells.nix { inherit pkgs groups; };

      nixosModules.default = import ./nix/module.nix;

      overlays.default = _final: _prev: {
        agent-toolbox = self.packages.${system}.agent-toolbox;
      };

      lib.${system} = {
        inherit groups;
        inherit (toolbox) mkEnv mkToolbox;
      };

      formatter.${system} = pkgs.nixfmt-tree;

      checks.${system} = import ./tests { inherit self nixpkgs system; };
    };
}
