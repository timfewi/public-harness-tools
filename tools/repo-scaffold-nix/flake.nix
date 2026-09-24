{
  description = "Fail-closed repository scaffolder and flake templates for .project-checks.json";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/eaad089433ca2bb662274377d33df3d0e51ef28b";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      projectScaffold = import ./packages/project-scaffold.nix { inherit pkgs; };
    in
    {
      packages.${system} = {
        default = projectScaffold;
        project-scaffold = projectScaffold;
      };

      templates = {
        default = {
          path = ./templates/default/files;
          description = "Nix project with formatter, statix, deadnix and flake checks";
          welcomeText = "Stage the scaffold, then run `project-check fast`.";
        };
        rust = {
          path = ./templates/rust/files;
          description = "Rust project with cargo fmt/clippy/test plus the Nix checks";
          welcomeText = "Stage the scaffold, then run `project-check fast`.";
        };
        python = {
          path = ./templates/python/files;
          description = "Python project with ruff plus the Nix checks";
          welcomeText = "Stage the scaffold, then run `project-check fast`.";
        };
        web = {
          path = ./templates/web/files;
          description = "Web/UI project with a visual QA configuration plus the Nix checks";
          welcomeText = "Stage the scaffold, point `.visual-qa.config.json` at your dev server, then run `project-check fast`.";
        };
      };

      nixosModules.default = import ./nix/module.nix { inherit self; };

      formatter.${system} = pkgs.nixfmt-tree;

      checks.${system} = import ./tests { inherit nixpkgs system; };
    };
}
