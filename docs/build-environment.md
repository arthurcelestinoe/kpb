# Initial KPB build environment

## Status and scope

This document records the approved prefix, dependency composition, discovery environment, and isolation direction for the first functional milestone. These are requirements for a future implementation; no build environment, resolver, Bubblewrap executor, or Nix integration is implemented yet.

The milestone builds project-maintained [recipes](recipes.md) and produces validated artifacts in staging. It does not install packages into the host, define an installed-package database, or select a packaged archive format.

## Prefix and staging

The initial prefix is fixed at `/opt/kpb`. KPB supplies `prefix=/opt/kpb` to each recipe. The prefix exists inside the build sandbox; KPB must not create or populate the host's `/opt/kpb` in this milestone.

Each build has a dependency tree exposed at `/opt/kpb` and a separate staging root for the current package:

```text
Inside the sandbox:
  /opt/kpb/bin                 dependency tools (read-only)
  /opt/kpb/include             dependency headers (read-only)
  /opt/kpb/lib                 dependency libraries (read-only)
  /opt/kpb/lib/pkgconfig       dependency metadata (read-only)

Current package output:
  $pkgdir/opt/kpb/...          staged package files
```

For example, a recipe configured with `--prefix="$prefix"` can stage an installation using `make DESTDIR="$pkgdir" install`, when its build system supports `DESTDIR`. It must not install directly into `/opt/kpb`. The current package's staging tree is not incorporated into its dependency tree during its own build.

Artifacts are built for `/opt/kpb`. Relocation is not guaranteed, and configurable prefixes are deferred. This decision does not select a future host installation layout or a host activation mechanism for executables and libraries.

## Dependency composition

Build the required dependencies before their consumer and compose the tree only from validated package artifacts. Preserve the inputs; composition and consumer builds must not modify those artifacts.

For the package being built, the tree contains:

- Its direct `depends` and `makedepends` packages.
- Its direct `checkdepends` packages only when `check()` is enabled and will run.
- The transitive runtime dependencies needed by every included package, including build and test tools.

A package's own build-only and test-only dependencies are needed when building that package, but are not automatically carried into its consumer's tree. Dependency roles remain distinguishable even when a package is required in more than one role. Disabling tests removes test-only requirements, not packages also required through another role.

For example, suppose `app` declares `depends=('liba')` and `makedepends=('generator')`. If `generator` needs `supportlib` at runtime, the app's build tree includes `supportlib`. If `generator` used `compiler` only to build itself, that fact alone does not add `compiler` to the app's tree.

### Versions, collisions, and ownership

Each build tree permits one version per package name. Conflicting exact-version requirements stop resolution; KPB must not automatically build alternative dependency trees to satisfy incompatible consumers in this milestone. This is a per-tree rule, not a promise that only one version can ever exist among stored artifacts.

Shared directories may be merged. Reject collisions between files or symbolic links, even when their contents or targets match, and reject incompatible entry types such as a file and a directory at the same path. Never silently overwrite or choose a winning package based on composition order.

Keep the originating package identifiable for each contributed entry, including the contributors to shared directories. This ownership information is required for composition diagnostics; its storage format and any future installed-package database remain undecided.

### Temporary bootstrap inputs

Temporary Nix tools remain separate from the tree of KPB-managed packages. Declare them explicitly through bootstrap configuration, not by converting recipe dependency names into Nix package names. Supply the tools and their required runtime inputs for build use without changing the user's profiles or shell configuration.

KPB-managed tools take precedence through the discovery environment below. A missing tool must not trigger a fallback to the user's PATH or undeclared host packages. Replacing a temporary Nix input with a validated project recipe remains the intended migration path.

Define the temporary Nix tool set in a version-controlled `flake.nix`, with a version-controlled `flake.lock` pinning the nixpkgs revision and other inputs. Nix and flake support must already be available; KPB must not install Nix, enable experimental features, or change user/system configuration automatically. Missing support requires an actionable diagnostic before build execution.

Normal builds must use the committed lock without generating or updating it. A missing lock, or a definition that requires changing it, must stop the operation rather than silently select new inputs. Lock updates are an explicit maintainer operation, reviewed with the bootstrap definition. Pinning inputs alone does not prove reproducibility, isolation, or runtime independence from Nix.

The exact tool list and pinned versions, mapping and recording of recipe bootstrap exceptions, store mounts, and toolchain-specific adjustments remain separate decisions. No flake or lock is implemented yet. Nix is not a permitted runtime dependency provider for final artifacts.

## Discovery environment

KPB supplies the following environment for every recipe stage instead of inheriting the user's discovery settings:

| Setting | Initial behavior |
|---|---|
| `prefix` | `/opt/kpb` as a recipe variable. |
| `PATH` | `/opt/kpb/bin`, followed only by tool directories explicitly supplied through bootstrap configuration. No inherited PATH entries. |
| `PKG_CONFIG_LIBDIR` | `/opt/kpb/lib/pkgconfig:/opt/kpb/share/pkgconfig`. |
| `PKG_CONFIG_PATH` | Unset; do not inherit the user's additional search paths. |
| `CMAKE_PREFIX_PATH` | `/opt/kpb`. |
| Compiler/linker flags | No automatically added flags or inherited user flags; required adjustments are explicit in the recipe. |
| `LD_LIBRARY_PATH` | Not automatically set or inherited; any necessary recipe adjustment must be explicit. |

These settings facilitate discovery; they do not guarantee that every build system or compiler uses the intended paths. KPB must not expose host directories and libraries as implicit dependencies. Toolchain defaults, embedded search paths, and runtime loading require explicit treatment and validation.

The prefix alone does not make a library discoverable by the runtime loader. Libraries, interpreters, and loaders required by the final result must be accounted for explicitly. The initial runtime search policy is defined below; the detailed compiler/linker configuration and runtime validation mechanism are not selected here.

### Initial C runtime

glibc is the selected C runtime for the initial bootstrap and dynamically linked package demonstration. Build glibc and its runtime loader through a project-maintained recipe for the `/opt/kpb` environment; do not introduce a preliminary musl-based runtime stage.

Nix may supply the compiler and other temporary build tools, but the final packages must use the KPB-built runtime rather than glibc or a loader from the Nix store or an undeclared host installation. This is an approved direction, not an implemented or validated bootstrap chain.

The initial target is native x86_64 Linux, and the package demonstration is limited to C. GCC and GNU Binutils will be supplied temporarily through Nix. C++ packages and provision of a KPB-built libstdc++ runtime are deferred; this does not change Rust as KPB's implementation language.

Use the KPB-built loader under `/opt/kpb/lib` and explicit ELF `DT_RUNPATH` entries pointing to `/opt/kpb/lib` in executables and libraries that need this runtime search path. Apply the required linker settings explicitly in the recipes, not as automatically injected KPB flags. Do not depend on host loader configuration, a private loader cache as the initial discovery mechanism, or inherited `LD_LIBRARY_PATH`.

Each library must account for its own dynamic dependencies rather than assume the executable's RUNPATH covers every transitive dependency. The validation sandbox must provide the KPB-built runtime and declared runtime dependencies while withholding the Nix store and undeclared host runtime libraries. Targeting C alone does not prove that compiler support libraries are absent; any required runtime component must also meet the existing ownership and Nix-independence rules.

The glibc version, prerequisite recipes, exact loader filename, compiler/linker and startup-object configuration, and bootstrap input versions remain to be defined. Selecting glibc and RUNPATH does not remove those bootstrap requirements or establish a host installation layout.

## Isolation boundary

Bubblewrap is the selected basis for build isolation. The dependency tree is exposed read-only. Recipe functions run without network access, with writes restricted to the workspace, staging, and private temporary directories. User home contents, credentials, session sockets, and host packages must not become implicit build inputs.

KPB must check effective isolation support on the host rather than only the presence of the `bwrap` command. If the required baseline cannot be established, stop with an actionable diagnostic instead of running an unprotected build. Additional protections may vary by host, but must not silently weaken this baseline.

The full mount layout, per-stage permissions, namespace setup, environment allowlist, and resource limits remain to be specified. This document records the required boundary, not a complete sandbox implementation or proof of enforcement.

Using Nix-supplied build tools does not establish isolation or ensure that produced binaries are independent of Nix. Final artifact validation must examine runtime libraries, interpreters, loaders, and store references. Reject artifacts with Nix runtime dependencies or whose runtime independence cannot be demonstrated. Do not use inherited host paths or an automatically supplied `LD_LIBRARY_PATH` to hide missing runtime requirements.

## Future implementation validation

These are requirements for future tests, not tests of existing KPB functionality:

- Compose direct build/runtime/test requirements and their runtime closure; do not propagate dependencies used only to build an already completed dependency.
- With tests disabled, omit test-only requirements while retaining packages also needed for build or runtime.
- Accept compatible requirements for one version; reject conflicting versions without automatic alternative builds.
- Merge shared directories, preserve contributor ownership, and reject file, link, and entry-type collisions without overwriting inputs.
- Keep the dependency tree read-only, preserve validated source artifacts, and keep current staging separate throughout the build.
- Verify `prefix=/opt/kpb`, output under `$pkgdir/opt/kpb`, and no creation or population of the host's `/opt/kpb`.
- Verify discovery by PATH, pkg-config, and CMake; exclude inherited user paths, flags, and runtime search settings.
- Verify a missing declared tool fails rather than using a host tool, and that explicit bootstrap tools remain distinct from KPB-managed packages.
- Require pre-existing Nix flake support and a committed, usable bootstrap lock; verify normal builds do not modify it, silently update inputs, or change Nix configuration.
- Verify the required Bubblewrap boundary, diagnostics for unavailable isolation, and absence of network access from recipe functions.
- Reject final artifacts with Nix runtime dependencies or unverified runtime independence, including cases where inherited host settings would otherwise mask missing dependencies.
- Verify that the dynamic demonstration uses the KPB-built glibc and loader, and can run in its validation sandbox without the Nix store or undeclared host runtime libraries.
- Verify the initial native x86_64 C target, loader placement under `/opt/kpb/lib`, and explicit RUNPATH for executables and libraries requiring it, including transitive library dependencies without a host cache or inherited `LD_LIBRARY_PATH`.

The database, host installation/removal behavior, archive format, relocation support, and prefix configurability are outside this milestone. They must not be inferred from this build-time prefix and dependency layout.
