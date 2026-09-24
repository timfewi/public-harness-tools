{
  nixpkgs,
  system,
}:
let
  pkgs = nixpkgs.legacyPackages.${system};
  src = pkgs.lib.fileset.toSource {
    root = ../.;
    fileset = pkgs.lib.fileset.unions [
      ../flake.nix
      ../nix
      ../packages
      ../runtime
      ../templates
      ../tests
    ];
  };
in
{
  python-tests =
    pkgs.runCommand "repo-scaffold-python-tests"
      {
        nativeBuildInputs = [
          pkgs.git
          pkgs.python3
        ];
        PROJECT_SCAFFOLD_TEMPLATES = ../templates;
      }
      ''
        cd ${src}
        python3 -m unittest discover -s tests -t . -p 'test_*.py' -v
        touch "$out"
      '';

  template-integrity =
    pkgs.runCommand "repo-scaffold-template-integrity"
      {
        nativeBuildInputs = [ pkgs.python3 ];
      }
      ''
        python3 ${./template-integrity.py} ${../templates}
        touch "$out"
      '';

  lint =
    pkgs.runCommand "repo-scaffold-lint"
      {
        nativeBuildInputs = [
          pkgs.deadnix
          pkgs.statix
        ];
      }
      ''
        cd ${src}
        statix check .
        deadnix --fail .
        touch "$out"
      '';
}
