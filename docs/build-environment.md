# KPB build environment

## Status and scope

The initial milestone builds project-maintained [recipes](recipes.md), reuses explicitly validated installed host dependencies to minimize compilation, and produces validated artifacts in staging. Host-bound artifacts are permitted. The resolver, general host providers, recipe executor, and final artifact validator remain unimplemented; the [host-GCC experiment](host-dependencies.md#local-experiment) provides bounded evidence for this direction.

This milestone does not install packages into the host, define an installed-package database, or select a packaged archive format. The runtime may come from the host; KPB need not build an independent compiler, C library, or loader before building applications.

## Prefix and staging

KPB supplies the fixed `prefix=/opt/kpb` to recipes. Its own dependency tree is read-only there inside the sandbox; the current package writes under a separate `$pkgdir/opt/kpb`. This does not create or populate `/opt/kpb` on the host.

```text
Inside the sandbox:
  /opt/kpb/...                 validated KPB-managed dependencies, read-only
  provider-approved paths     selected host tools/headers/libraries, read-only
  controlled command dir      selected host command aliases, read-only

Current package output:
  $pkgdir/opt/kpb/...          staged package files
```

For a build system honoring `DESTDIR`, `make DESTDIR="$pkgdir" install` stages files beneath `$pkgdir/opt/kpb`; it must not install directly into the dependency prefix. Current staging is not incorporated into its own dependency tree.

Approved host components retain the canonical paths their interpreters, wrappers, and loaders require. Their presence does not change the installation prefix for KPB-managed files. Artifacts are bound to the selected prefix and recorded host/runtime compatibility; relocation and cross-distribution portability are not guaranteed. Configurable prefixes and future host installation/activation remain separate decisions.

## Dependency selection and composition

Reuse compatible validated dependencies already available from installed host components or validated KPB artifacts. Build a project recipe only when its requirement is not otherwise satisfied. No persistent artifact-cache implementation is specified here.

Resolve these requirements and their transitive dependencies before executing recipes:

- Direct `depends` and `makedepends`.
- `checkdepends` only when `check()` will run.
- Runtime components needed by selected build/test tools and target packages, including interpreters, loaders, libraries, and required toolchain resources.

Keep roles and providers explicit. Do not propagate dependencies used only to build a completed dependency into its consumer's tree. Disabling tests removes only test-exclusive requirements.

Include auxiliary tool requirements declared by KPB's [probe registry](dependency-catalog.md#auxiliary-tools-belong-to-the-probe-registry) in validation planning. Resolve and validate them before running their dependent probes, using host components or available validated artifacts/buildable recipes. If they cannot be satisfied, report the validation requirement and stop. These tools are not automatically application runtime dependencies, and catalog entries do not redeclare them.

A provider's declared package dependencies or file list alone may not describe the complete toolchain. Account for compiler subprocesses, assemblers/linkers, plugins, specs, headers, data files, and target/runtime search paths as required by the selected operation. The fact that the compiler needs a library to execute does not automatically declare it as an application runtime dependency.

### Missing requirements and diagnostics

Plan the full selected graph before obtaining package sources or executing `prepare()`, `build()`, `check()`, or `package()`. If any requirement has no compatible validated installed host component, reusable validated KPB artifact, or project recipe whose own dependency graph can be satisfied, stop. Do not start a partial build or report incomplete staging as a valid artifact.

Report all known unresolved requirements together, including:

- Logical dependency name and requested version/constraint.
- Build, runtime, or enabled test role.
- Requiring package and transitive chain where applicable.
- Candidates found and the reason they could not satisfy the requirement.
- Whether the component is confirmed missing, incompatible, or could not be established because provider information/mapping is unavailable.

For example, if `app` needs a recipe for `libexample`, and that recipe needs unavailable `bison` with no recipe of its own, report `app -> libexample -> bison`, not just that `libexample` could not be built. Keep version conflicts, cycles, ambiguous ownership, integrity failures, and unavailable isolation distinguishable from ordinary missing dependencies.

The user can install the reported requirements through the host's own tools or provide suitable recipes and rerun KPB. KPB must not automatically install host packages, fetch replacement tools, enable package-manager features, or alter profiles, shell configuration, or package databases. A runtime component discovered to be unresolved during final validation also stops artifact acceptance with an actionable diagnostic.

This is the required behavior for the future resolver/executor; it is not an implemented missing-dependency CLI.

### Versions, collisions, and ownership

Apply the [provider/candidate selection policy](host-dependencies.md#provider-and-candidate-selection) while planning dependencies: prefer capable PackageKit, use approved native providers when needed, and unify consistent evidence only for the same component/files with origins retained. If distinct candidates are equally valid, stop for explicit user selection; report contradictions and never bypass validation. Do not use PATH order, catalog order, or highest version as an implicit tie-breaker. This does not override catalog mapping ambiguity diagnostics.

Select one version/provider per logical dependency in a build graph. Conflicting exact constraints stop resolution; do not automatically construct alternative version trees. Preserve the distinction between KPB `pkgver`, native package version/revision/epoch, effective tool version, and ABI compatibility. Provider/name mapping remains explicit.

Compose validated KPB artifacts read-only at `/opt/kpb`. Merge shared directories while preserving contributor ownership; reject file, symlink, and incompatible entry-type collisions, including mount destination collisions. Never silently overwrite entries or shadow one dependency with another. Preserve input artifacts and keep current staging separate.

Record the provider, package/component identity, files/canonical paths, available versions, integrity evidence, dependency roles, and transitive relationships for selected host components. Proposed provider details and experimental limits are in [host-dependencies.md](host-dependencies.md).

Apply [the minimum host evidence](host-dependencies.md#minimum-host-dependency-evidence) before selecting a host candidate: ownership/files, compatibility, provider-offered integrity checks, and a functional probe in Bubblewrap. Tools must execute with the required effective identity/version; library probes must compile, link, and execute against the selected development/runtime components. Record unavailable integrity functionality explicitly; actual content mismatches reject the candidate, and failed offered checks must not be relabeled as unsupported. Without enough evidence, use a validated artifact/buildable recipe or report the unresolved requirement and stop.

## Discovery environment

PATH can locate candidates during host discovery; it is not proof of ownership, version, integrity, or compatibility. Recipe stages receive a controlled environment after validation:

| Setting | Behavior |
|---|---|
| `prefix` | `/opt/kpb` as a recipe variable. |
| `PATH` | `/opt/kpb/bin`, then an isolated command directory containing only explicitly selected validated host commands. No inherited host PATH. |
| `PKG_CONFIG_LIBDIR` | `/opt/kpb/lib/pkgconfig:/opt/kpb/share/pkgconfig`, plus only selected and validated host metadata locations from the dependency plan. |
| `PKG_CONFIG_PATH` | Unset; never inherit the user's additional paths. |
| `CMAKE_PREFIX_PATH` | `/opt/kpb`, plus only explicitly selected validated host search locations. |
| Compiler/linker flags | No inherited user flags or globally injected flags. Necessary recipe-specific adjustments remain explicit. |
| Compiler search overrides | Clear inherited variables such as `CPATH`, `C_INCLUDE_PATH`, `CPLUS_INCLUDE_PATH`, `COMPILER_PATH`, `LIBRARY_PATH`, and `GCC_EXEC_PREFIX`. |
| `LD_LIBRARY_PATH` / `LD_PRELOAD` | Unset and not inherited or automatically supplied. Any recipe-specific runtime search adjustment must be explicit and validated. |

Search variables do not replace filesystem isolation. Native compiler defaults can be used only where their required files are part of the approved mount plan. Do not expose all of `/usr`, `/usr/bin`, `/lib`, the Nix store, or the user's profile merely to make tools work. A selected package output can contain additional commands; read-only package exposure is not an executable allowlist.

## Runtime and compatibility

Host-provided runtimes, including registered Nix/NixOS components, are allowed when explicitly identified, selected, and validated. Store paths alone are not rejection criteria. KPB need not supply its own glibc, libgcc, or dynamic loader.

Before accepting an artifact, validate interpreters, loaders, dynamic libraries, static link contributions, runtime paths, and required transitive components against the recorded dependency plan. An executable's RUNPATH does not automatically satisfy every transitive library. Do not inherit loader configuration or expose a host cache indiscriminately; any required configuration must be explicitly approved and recorded.

Record the target architecture and relevant host/runtime/ABI requirements. Host-bound acceptance does not promise that an artifact works on another distribution, after incompatible host upgrades, or after a referenced store path is removed. The precise compatibility metadata, lifetime/snapshot strategy, and general validator remain to be implemented.

## Isolation boundary

Bubblewrap remains mandatory. Expose source/dependency/tool inputs read-only, deny external network access to recipe functions, and restrict writes to private workspace, staging, and temporary directories. Exclude user home contents, credentials, session sockets, provider daemons/sockets, and undeclared host data. Perform provider queries and controlled source acquisition outside recipe execution.

Check effective isolation, not just whether `bwrap` exists. Require the intended user/mount/PID/network/IPC/UTS boundaries, cleared environment, dropped privileges/capabilities, and read-only mounts. If the baseline is unavailable, stop with an actionable diagnostic; do not run the build without it. Additional host protections may vary.

The full production mount layout, per-stage write permissions, environment allowlist, and resource limits remain separate decisions. The [host-tool experiment](host-dependencies.md#local-experiment) validates a bounded layout on native x86_64 NixOS; it is not the general recipe executor or a complete security policy.

## Future implementation validation

These are requirements for future tests, not claims of implemented resolver/executor behavior:

- Reuse compatible validated installed host dependencies without unnecessary recipe builds.
- Require known ownership/files, compatible tool identity/version/architecture or library development/runtime components, offered integrity checks, and successful functional probes inside Bubblewrap.
- Record unsupported integrity capabilities without claiming verified contents; never treat denied/inconclusive/failed offered checks as unsupported. Reject content mismatches even when a functional probe succeeds.
- Exercise tool execution and library compile/link/run probes using only selected inputs. If evidence is insufficient or a probe fails, use a viable recipe/artifact or stop with diagnostics; never weaken isolation.
- Build an available project recipe when a requirement cannot be satisfied by already available components and its full graph is resolvable.
- With missing direct/transitive requirements and no buildable recipes, aggregate diagnostics and stop before source acquisition or recipe execution; never install host packages automatically.
- Distinguish confirmed absence, unavailable provider evidence, version/ABI mismatch, ownership ambiguity, integrity failure, conflicts, and cycles.
- Prefer PackageKit when sufficient; use approved native providers for missing required capabilities. Preserve origins when unifying evidence for the same component/files, and diagnose conflicting evidence without suppressing failed checks.
- With distinct equally valid candidates, stop and present them for explicit selection. Verify selection cannot waive validation or resolve the tie implicitly through PATH/catalog order or highest version.
- Include enabled test dependencies and selected tools' runtime/resource closures; omit test-only requirements when tests are disabled and build-only inputs used solely to produce completed dependencies.
- Merge shared directories, preserve provider/ownership information, and reject version/file/link/type/mount collisions.
- Keep dependency inputs read-only and staging separate; verify `/opt/kpb` staging without writes to the host prefix.
- Verify controlled PATH/pkg-config/CMake discovery and removal of inherited compiler/loader search overrides.
- Verify required Bubblewrap namespaces, nonroot execution, environment cleanup, hidden user data, blocked external networking, and failure when isolation is unavailable.
- Accept explicitly validated host-bound runtimes, including Nix store components on Nix hosts; reject unapproved/unresolved/incompatible runtime requirements without making portability claims.
- Record provenance and detect stale host observations; do not claim an atomic snapshot without implementing one.

The database, host installation/removal, archive format, relocation, and prefix configurability remain outside this milestone.
