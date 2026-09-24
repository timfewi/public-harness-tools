{ pkgs }:
let
  script = pkgs.writeText "project_scaffold.py" (
    builtins.replaceStrings [ "@templates@" ] [ (toString ../templates) ] (
      builtins.readFile ../runtime/project_scaffold.py
    )
  );
in
pkgs.writeShellApplication {
  name = "project-scaffold";
  runtimeInputs = [
    pkgs.git
    pkgs.python3
  ];
  text = ''
    exec ${pkgs.python3}/bin/python3 -I ${script} "$@"
  '';
}
