# SPDX-License-Identifier: GPL-3.0-or-later
{
  description = "Temporary, pinned bootstrap tools for Kobalt Package Builder";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33";

  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config = { };
        overlays = [ ];
      };

      # Adding libraries is not enough: configure may silently omit MPFR.
      mpfrProbe = ''
        BEGIN {
          actual = sprintf("%.0f", (2 ^ 100) + 1)
          if (actual != "1267650600228229401496703205377") {
            print "Gawk bootstrap requires working GMP/MPFR arithmetic" > "/dev/stderr"
            exit 1
          }
          print "GMP/MPFR arithmetic verified"
        }
      '';

      gawkMpfr = pkgs.gawk.overrideAttrs (old: {
        buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.gmp pkgs.mpfr ];
        configureFlags = (old.configureFlags or [ ]) ++ [ "--with-mpfr" ];
        doInstallCheck = true;
        installCheckPhase = ''
          runHook preInstallCheck
          "$out/bin/gawk" -M -v PREC=256 ${pkgs.lib.escapeShellArg mpfrProbe}
          runHook postInstallCheck
        '';
      });

      recipeTools = {
        inherit (pkgs)
          bashNonInteractive
          coreutils
          findutils
          diffutils
          gnugrep
          gnused
          gnumake
          gcc
          binutils
          bison
          gnum4
          python3
          perl
          texinfo
          gettext
          gnupatch
          rsync
          ;
        gawk = gawkMpfr;
      };

      orchestrationTools = {
        inherit (pkgs) curl cacert gnutar gzip xz bubblewrap binutils;
      };

      recipeBundle = pkgs.buildEnv {
        name = "kpb-bootstrap-recipe-tools";
        paths = pkgs.lib.attrValues recipeTools;
        pathsToLink = [ "/bin" ];
        ignoreCollisions = false;
        passthru.toolVersions = pkgs.lib.mapAttrs (_: tool: tool.version) recipeTools;
      };

      orchestrationBundle = pkgs.buildEnv {
        name = "kpb-bootstrap-orchestration-tools";
        paths = pkgs.lib.attrValues orchestrationTools;
        pathsToLink = [ "/bin" "/etc/ssl/certs" ];
        ignoreCollisions = false;
        passthru.toolVersions = pkgs.lib.mapAttrs (_: tool: tool.version) orchestrationTools;
      };
    in
    {
      packages.${system} = {
        bootstrap-recipe-tools = recipeBundle;
        bootstrap-orchestration-tools = orchestrationBundle;
        gawk-mpfr = gawkMpfr;
      };

      checks.${system} = {
        gawk-mpfr = pkgs.runCommand "kpb-gawk-mpfr-check" { } ''
          ${gawkMpfr}/bin/gawk -M -v PREC=256 ${pkgs.lib.escapeShellArg mpfrProbe} > "$out"
        '';

        bootstrap-layout = pkgs.runCommand "kpb-bootstrap-layout-check" { } ''
          for tool in bash sh cat cp install find xargs diff grep sed awk gawk \
            make gcc cc as ld ar readelf bison m4 python3 perl makeinfo msgfmt patch rsync; do
            if ! test -x "${recipeBundle}/bin/$tool"; then
              echo "Missing executable in recipe tools: $tool" >&2
              exit 1
            fi
          done

          for tool in curl tar gzip xz bwrap readelf; do
            test -x "${orchestrationBundle}/bin/$tool"
          done
          test -s "${orchestrationBundle}/etc/ssl/certs/ca-bundle.crt"

          # This checks PATH grouping, not confinement of executable closures.
          for tool in curl tar gzip xz bwrap nix git; do
            if test -e "${recipeBundle}/bin/$tool"; then
              echo "Unexpected orchestration or undeclared recipe tool: $tool" >&2
              exit 1
            fi
          done
          touch "$out"
        '';
      };
    };
}
