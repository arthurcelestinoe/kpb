# Initial bootstrap tools

## Status and scope

This document selects the initial tools from the fixed nixpkgs revision in [bootstrap-versions.md](bootstrap-versions.md), for native `x86_64-linux` builds of project-maintained Linux headers, glibc, and the C demonstration chain. The root flake now supplies the tool bundles and checks described in [bootstrap-flake.md](bootstrap-flake.md). No recipe executor or recipes are implemented yet; successful tool checks do not establish a working KPB package build.

There are two roles: tools supplied to the initial recipe build processes, and tools used by KPB's orchestration. These roles describe exposure, not new resolver/provider abstractions. The tool set can be revised explicitly if implementation reveals additional requirements; missing tools must produce diagnostics, not an automatic fallback to the host.

## Recipe build tools

Select these 18 nixpkgs attributes for the initial bootstrap recipe environment. Their runtime closures are required to execute them, but are not permitted runtime dependencies of final KPB artifacts.

| Attribute | Version | Purpose |
|---|---|---|
| `bashNonInteractive` | 5.3p9 | Recipe stages and build scripts; no interactive shell setup. |
| `coreutils` | 9.11 | File operations, installation into staging, text utilities, and checksums. |
| `findutils` | 4.10.0 | File traversal and argument processing. |
| `diffutils` | 3.12 | Source/build comparisons and tests. |
| `gnugrep` | 3.12 | Pattern searches used by configure scripts, builds, and tests. |
| `gnused` | 4.10 | Source/header transformations and configure scripts. |
| `gawk` (explicit MPFR-enabled variant) | 5.4.1 | glibc code generation and tests requiring high-precision arithmetic. |
| `gnumake` | 4.4.1 | Linux header export, glibc, and the C demonstration builds. |
| `gcc` | 15.3.0 | Temporary C compiler, including compilation of build-time helper programs. |
| `binutils` | 2.46 | GNU assembler, linker, archiver, and ELF tools. |
| `bison` | 3.8.2 | Parser generation required by glibc. |
| `gnum4` | 1.4.21 | Macro processor used by Bison. |
| `python3` | 3.13.17 | glibc build and test scripts. |
| `perl` | 5.42.3 | Header-generation scripts and applicable glibc tests/utilities. |
| `texinfo` | 7.2 | glibc documentation generation and installation. |
| `gettext` | 1.0 | Message catalog tools used by the reference glibc build. |
| `gnupatch` | 2.8 | Explicit application of verified local patches during preparation. |
| `rsync` | 3.5.0 | The Linux `headers_install` export target. |

Rationale beyond the [glibc 2.42 tool requirements](https://sourceware.org/glibc/manual/2.42/html_node/Tools-for-Compilation.html):

- Linux's [`headers_install` target](https://github.com/torvalds/linux/blob/v6.18/Makefile) uses rsync to export the generated headers. Selecting rsync allows the future recipe to use that target instead of requiring a custom replacement. This inspection does not select the exact Linux source version for the KPB recipe.
- The pinned nixpkgs [Linux headers definition](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/os-specific/linux/kernel-headers/default.nix) explicitly uses Perl and a build compiler. It replaces the rsync-based installation with a copy operation; KPB has not adopted that replacement.
- The pinned [Bison definition](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/by-name/bi/bison/package.nix) propagates M4. Include it explicitly rather than relying on undocumented propagation into the build environment.
- The pinned [glibc definition](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/development/libraries/glibc/common.nix) includes gettext among its native build inputs. Carry that role explicitly while the KPB glibc source/patch set is being defined.

These are tools for the initial bootstrap chain, not implicit dependencies for every future recipe. Availability in this set must not automatically satisfy a named recipe dependency. Mapping explicit bootstrap exceptions to declared dependencies, and recording their use, remains to be defined separately from the recipes.

### Explicit Gawk variant for glibc tests

The default [Gawk definition in the snapshot](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/tools/text/gawk/default.nix) does not include GMP/MPFR build inputs. The glibc requirements call for Gawk with MPFR support for testing. Therefore the selected Gawk root is an explicit `overrideAttrs` variant of this same package, preserving its version and source, appending `gmp` 6.3.0 and `mpfr` 4.2.2 to `buildInputs`, and appending `--with-mpfr` to its existing `configureFlags`.

This is the only selected package override, not permission to change the snapshot or apply arbitrary overlays. GMP and MPFR are support dependencies of the bootstrap tool, not additional recipe PATH entries or final KPB runtime libraries. The flake includes a functional `gawk -M` check and fails if high-precision support is absent; configure detection alone may otherwise leave it disabled. The option was checked in the [official Gawk 5.4.1 source archive](https://ftp.gnu.org/gnu/gawk/gawk-5.4.1.tar.xz). The variant has since been built and passed its installation and flake precision checks; see [executed validation](bootstrap-flake.md#executed-validation-and-limits).

## Orchestration tools

Select these seven attributes for the operations controlled by KPB. Do not append their directories to recipe PATH merely because the orchestrator needs them. Binutils has a role in both groups; it is the same pinned package, not a separately selected toolchain.

| Attribute | Version | Purpose |
|---|---|---|
| `curl` | 8.23.0 | HTTPS source acquisition before recipe functions execute. |
| `cacert` | 3.131.1 | Explicit CA trust bundle for HTTPS acquisition. |
| `gnutar` | 1.35 | Handling supported tar archives after verification. |
| `gzip` | 1.14 | Decompression of supported `.tar.gz` sources. |
| `xz` | 5.8.4 | Decompression of supported `.tar.xz` sources. |
| `bubblewrap` | 0.12.0 | Establishing the required build and runtime-validation sandboxes. |
| `binutils` | 2.46 | ELF inspection, including readelf inspection of loaders, dynamic dependencies, and RUNPATH. |

This selects tools for external operations, not an implementation of downloading, extraction, hashing, or validation. HTTPS verification and an explicit trust bundle are required; insecure download bypasses are not part of the bootstrap. Archive path/link validation and collision checks remain KPB responsibilities; selecting GNU tar does not establish those guarantees by itself. ELF inspection alone does not prove runtime independence, which also requires controlled runtime validation.

## Exposure and boundaries

- Use the same fixed snapshot for both groups, with no profiles, registry substitutions, overlays, or moving-channel fallback. Apply only the documented Gawk variant above.
- Supply recipe PATH as documented in [build-environment.md](build-environment.md#discovery-environment): KPB-managed tools first, followed only by the selected bootstrap tool directories.
- Preserve the runtime closure required by the bootstrap tools, including their loader, libraries, and executable interpreter paths. The exact mounts and handling of shebang paths such as `/bin/sh` remain executor decisions; selecting Bash alone is not their implementation.
- PATH grouping is not a command-execution allowlist. Runtime closures may contain additional executables. Enforce the Bubblewrap filesystem and network boundary independently; recipe functions still have no network even if they locate a network-capable executable.
- Nix remains the pre-existing bootstrap management prerequisite. Do not expose its CLI or daemon socket to recipes as build tools.
- Resolve/download bootstrap inputs before the network-isolated recipe stages. Keep Nix tools separate from `/opt/kpb` and reject their use as final artifact runtime dependencies.

## Exclusions and test coverage

Do not add CMake, Ninja, Meson, pkg-config, Git, Rust/Cargo, fakeroot, patchelf, Autoconf, Automake, Libtool, or Flex as bootstrap recipe tools in this step. They have no selected role in the initial headers/glibc/C chain; later recipes may require an explicit addition. Rust/Cargo are a separate requirement for developing KPB itself. Configuring `CMAKE_PREFIX_PATH` or pkg-config search paths does not imply those tools are installed.

GDB and Python PExpect are not selected initially. The glibc manual identifies them as requirements for its debugger pretty-printer tests, so those tests may report `UNSUPPORTED`; do not report full test coverage. Ordinary `check()` stages still run by default, and actual failures must not be silently ignored or tests globally disabled to compensate for a missing dependency.

## Verification and remaining work

During tool selection on 2026-11-07, all 18 recipe entries and all seven orchestration entries resolved, and nixpkgs `lib.meta.availableOn` returned true for `x86_64-linux` for every entry. The Gawk variant was separately evaluated: its version remains 5.4.1, its added inputs resolve to GMP 6.3.0 and MPFR 4.2.2, and its flags include `--with-mpfr`. Its declared platform availability is also true. Selection initially used metadata only; subsequent flake validation built the bundles and Gawk and executed the checks documented in [bootstrap-flake.md](bootstrap-flake.md).

Metadata availability is not proof of binary-cache availability, successful recipe compilation, test coverage, or sandbox compatibility. The flake/lock now implements the tool supply and checks executable paths and Gawk precision. Recipe exception mapping, source/patch selection, compiler wrapper integration, and the detailed sandbox policy remain separate work.

The [synthetic Bubblewrap check](bootstrap-sandbox.md) has also passed on the current x86_64 host, executing all 18 tool roles and compiling a C object inside the prototype sandbox. This does not demonstrate complete recipe builds or Nix-independent runtime.
