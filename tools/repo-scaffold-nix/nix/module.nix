{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.repoScaffold;
in
{
  options.programs.repoScaffold.enable = lib.mkEnableOption "the fail-closed project-scaffold repository scaffolder";

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [
      self.packages.${pkgs.stdenv.hostPlatform.system}.project-scaffold
    ];
  };
}
