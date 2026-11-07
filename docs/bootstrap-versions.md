# Initial bootstrap version selection

## Selected nixpkgs revision

For the initial `x86_64-linux` bootstrap, select:

- Repository: [NixOS/nixpkgs](https://github.com/NixOS/nixpkgs).
- Revision: [`c56a87d8e41ce69bd2af57eb35dcc117a9dfca33`](https://github.com/NixOS/nixpkgs/commit/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33).
- Branch of origin: `nixos-26.05`; the observed commit is dated 2026-11-05.
- Selection and evaluation date: 2026-11-07.
- Flake input: `github:NixOS/nixpkgs/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33`.
- Nix-generated locked content hash: `sha256-/cpdPHaySDIyCgZI6EWngiM6jK3YLUNzv1b7lTzy6Bk=`.

The commit, not the moving branch or the host's registry/channel, defines the selection. Use a release-line snapshot with a single coherent package set rather than independently mixing versions from different nixpkgs revisions. Do not add overlays or overrides implicitly. This does not require NixOS as the host distribution or a change to the host's Nix installation.

This document records the version baseline. The explicit initial tool set is selected in [bootstrap-tools.md](bootstrap-tools.md). The root flake and generated lock now implement its tool outputs and checks; usage and validation are recorded in [bootstrap-flake.md](bootstrap-flake.md). Recipe bootstrap exception mapping remains undecided.

## Evaluated tool versions

These versions were obtained by evaluating the selected source with `system = "x86_64-linux"`, `config = {}`, and `overlays = []`. The table records candidates available from the pinned set, not a requirement to expose every tool to every recipe.

The minimum versions below come from the [glibc 2.42 compilation requirements](https://sourceware.org/glibc/manual/2.42/html_node/Tools-for-Compilation.html).

| nixpkgs attribute | Evaluated version | glibc 2.42 minimum | Version check |
|---|---|---|---|
| `gcc` | 15.3.0 | 12.1 | Pass |
| `binutils` | 2.46 | 2.39 | Pass |
| `gnumake` | 4.4.1 | 4.0 | Pass |
| `gawk` | 5.4.1 | 3.1.2 | Pass |
| `bison` | 3.8.2 | 2.7 | Pass |
| `gnused` | 4.10 | 3.02 | Pass |
| `python3` | 3.13.17 | 3.4 | Pass |
| `texinfo` | 7.2 | 4.7 | Pass |

Additional evaluated versions used in the selected tool set:

| nixpkgs attribute | Evaluated version |
|---|---|
| `bashNonInteractive` | 5.3p9 |
| `coreutils` | 9.11 |
| `findutils` | 4.10.0 |
| `diffutils` | 3.12 |
| `gnugrep` | 3.12 |
| `gnutar` | 1.35 |
| `gzip` | 1.14 |
| `xz` | 5.8.4 |
| `perl` | 5.42.3 |

The subsequent tool-set evaluation also confirmed `gnum4` 1.4.21, `gnupatch` 2.8, `rsync` 3.5.0, `gettext` 1.0, `curl` 8.23.0, `cacert` 3.131.1, and `bubblewrap` 0.12.0. Their roles and exposure are specified in [bootstrap-tools.md](bootstrap-tools.md).

The tool-set decision requires an explicit MPFR-enabled variant of Gawk 5.4.1, with GMP 6.3.0 and MPFR 4.2.2 from this same snapshot. The default package is not sufficient evidence of that feature. The override, its evaluated inputs, and the implemented functional check are described in [bootstrap-tools.md](bootstrap-tools.md#explicit-gawk-variant-for-glibc-tests).

`gcc` and `binutils` are nixpkgs wrappers. Their reported upstream versions do not imply that their default include paths, startup objects, loader, flags, or runtime libraries are suitable for `/opt/kpb`. Recipe and bootstrap integration must address those explicitly. Do not assume that using the unmodified wrapper will produce a Nix-independent artifact.

## Runtime and header reference

At this revision, the nixpkgs glibc derivation is named `glibc-2.42-103`: its public `version` attribute is `2.42`, while its derivation version includes the stable-fix suffix `-103`. The [package definition](https://github.com/NixOS/nixpkgs/blob/c56a87d8e41ce69bd2af57eb35dcc117a9dfca33/pkgs/development/libraries/glibc/common.nix) applies a stable-branch patch and additional Nix-specific patches. Evaluation confirmed that this definition uses GCC 15.3.0 and Binutils 2.46.

This is the compatibility reference for selecting the bootstrap tools. It is not permission to use the Nix-built libc in final KPB packages, nor does it select the source and patch set for the future KPB glibc recipe. In particular, do not replace a maintained patched reference with an unreviewed bare release or copy Nix-specific patches automatically.

The evaluated `linuxHeaders` version is 6.18.7. This is a reference available in the snapshot, not a decision to require that running kernel or a substitute for the planned project-maintained headers recipe. The glibc documentation requires exported userspace headers rather than raw kernel source headers and distinguishes their version from the running kernel. See [glibc's Linux guidance](https://sourceware.org/glibc/manual/2.42/html_node/Linux.html).

## Verification and limits

Completed during the initial version selection, before the flake implementation:

- Resolved the release-line branch through the GitHub connector and downloaded the source archive by full commit into a temporary directory.
- Evaluated package versions locally with Nix 2.34.9, without building or installing packages, modifying profiles, or creating a project flake/lock. Nix evaluation caches used a task-specific temporary directory.
- Evaluated all eight minimum-version comparisons with nixpkgs `lib.versionAtLeast`; all returned true.
- Checked the effective glibc derivation version and the compiler/Binutils versions used by its definition, rather than relying only on package labels.

Meeting minimum versions is a compatibility screening result, not a successful glibc build. Some selected versions are newer than the newest tools listed as verified at the glibc 2.42 release. The nixpkgs definition also includes patches and build settings that KPB has not reproduced. Selection did not run executable probes or builds. Subsequent tool-bundle and Gawk checks are documented in [bootstrap-flake.md](bootstrap-flake.md); glibc tests, Bubblewrap confinement, and Nix-independent runtime remain unverified.

The implemented flake uses this exact revision and records its Nix-generated content hash in `flake.lock`; do not substitute a hash guessed from version labels or the commit identifier. Changes to the revision or package overrides require an explicit update and renewed evaluation. The isolation and runtime requirements in [build-environment.md](build-environment.md) still apply.
