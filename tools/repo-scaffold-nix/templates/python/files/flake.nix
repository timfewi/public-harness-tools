{
  description = "Project development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/eaad089433ca2bb662274377d33df3d0e51ef28b";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          bashInteractive
          basedpyright
          coreutils
          deadnix
          git
          jq
          just
          nixfmt
          python3
          ripgrep
          ruff
          statix
          uv
        ];
      };

      formatter.${system} = pkgs.nixfmt-tree;
    };
}
