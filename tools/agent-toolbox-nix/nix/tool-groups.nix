# Modular tool groups for coding agents.
#
# Each group is an independent, self-contained package list. A shell, the
# toolbox environment or a consuming host selects groups by name. Nothing here
# grants authority, network access, credentials or a sandbox; it only puts
# pinned executables on `PATH`. `sets.agent` is the default union, `sets.light`
# a small fallback for constrained hosts.
{ pkgs }:
let
  inherit (pkgs) lib;

  groups = {
    core = with pkgs; [
      bashInteractive
      coreutils
      findutils
      diffutils
      gnugrep
      gnused
      gawk
      ripgrep
      fd
      jq
      yq-go
      sd
      fzf
      bat
      eza
      tree
      less
      file
      which
      moreutils
      gnutar
      gzip
      bzip2
      xz
      zstd
      unzip
      zip
      neovim
    ];

    git = with pkgs; [
      git
      git-lfs
      gh
      delta
      tig
      openssh
      gnupg
    ];

    nix = with pkgs; [
      nix
      nixfmt
      deadnix
      statix
      direnv
      nix-direnv
      age
      sops
    ];

    search = with pkgs; [
      ripgrep
      fd
      ast-grep
      tree-sitter
      universal-ctags
      hyperfine
      tokei
    ];

    rust = with pkgs; [
      rustc
      cargo
      clippy
      rustfmt
      rust-analyzer
      cargo-nextest
      sqlite
    ];

    node = with pkgs; [
      nodejs
      bun
      pnpm
      yarn
      typescript
    ];

    python = with pkgs; [
      python3
      uv
      ruff
      basedpyright
    ];

    go = with pkgs; [
      go
      gopls
      gotools
    ];

    c = with pkgs; [
      clang
      clang-tools
      cmake
      gnumake
      ninja
      meson
      pkg-config
      lld
      valgrind
    ];

    lsp = with pkgs; [
      rust-analyzer
      typescript-language-server
      basedpyright
      nixd
      nil
      gopls
      taplo
      yaml-language-server
      bash-language-server
      lua-language-server
      clang-tools
      vscode-langservers-extracted
    ];

    lint = with pkgs; [
      shellcheck
      lua5_1.pkgs.luacheck
      statix
      deadnix
      ruff
      eslint
      prettier
      biome
      yamllint
      hadolint
      actionlint
      taplo
      semgrep
      osv-scanner
      gitleaks
    ];

    wasm = with pkgs; [
      wasmtime
      wasm-tools
      wit-bindgen
      cargo-component
    ];

    proto = with pkgs; [
      protobuf
      buf
      grpcurl
      protobuf-language-server
    ];

    runtime = with pkgs; [
      bubblewrap
      util-linux
      procps
      just
    ];
  };

  sets = groups // {
    light = lib.unique (groups.core ++ groups.git ++ groups.search ++ groups.nix ++ groups.runtime);
    agent = lib.unique (lib.concatLists (lib.attrValues groups));
  };

  names = builtins.attrNames groups;

  # Representative command per group, used by documentation and the module test.
  commands = {
    core = [
      "rg"
      "fd"
      "jq"
      "ls"
      "sed"
      "tree"
      "tar"
      "unzip"
    ];
    git = [
      "git"
      "gh"
      "delta"
      "git-lfs"
      "ssh"
      "gpg"
    ];
    nix = [
      "nix"
      "nixfmt"
      "statix"
      "deadnix"
    ];
    search = [
      "rg"
      "ast-grep"
      "tree-sitter"
      "ctags"
      "hyperfine"
      "tokei"
    ];
    rust = [
      "cargo"
      "rustc"
      "rust-analyzer"
      "rustfmt"
      "cargo-nextest"
      "sqlite3"
    ];
    node = [
      "node"
      "bun"
      "pnpm"
      "tsc"
    ];
    python = [
      "python3"
      "uv"
      "ruff"
      "basedpyright"
    ];
    go = [
      "go"
      "gopls"
    ];
    c = [
      "gcc"
      "clang"
      "cmake"
      "make"
      "ninja"
      "valgrind"
    ];
    lsp = [
      "rust-analyzer"
      "typescript-language-server"
      "basedpyright"
      "nixd"
      "nil"
      "gopls"
      "taplo"
    ];
    lint = [
      "shellcheck"
      "luacheck"
      "ruff"
      "eslint"
      "prettier"
      "biome"
      "yamllint"
      "hadolint"
      "actionlint"
      "semgrep"
      "osv-scanner"
      "gitleaks"
    ];
    wasm = [
      "wasmtime"
      "wasm-tools"
      "wit-bindgen"
    ];
    proto = [
      "protoc"
      "buf"
      "grpcurl"
    ];
    runtime = [
      "bwrap"
      "flock"
      "just"
    ];
  };
in
{
  inherit
    groups
    sets
    names
    commands
    ;
}
