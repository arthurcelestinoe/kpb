# Approved project decisions

## Status and scope

This is the authoritative architecture and first-milestone contract. It consolidates P01–P08, A01–A07 and B01–B03, approved on 2026-11-07, and C01–C03, approved together without amendments on 2026-11-09. Recipe and catalog syntax are owned by [recipes.md](recipes.md) and [dependency-catalog.md](dependency-catalog.md). Unresolved features are listed in [deferred-decisions.md](deferred-decisions.md); agent handling is defined in [AGENTS.md](../AGENTS.md#mandatory-decision-gate).

Approved requirements below are not claims of implemented features. Implementation status belongs in [CONTEXT.md](../CONTEXT.md); experiments are evidence only.

## Initial milestone

Project license: [GPL version 3 or later](../LICENSE).

- Validate local project-maintained recipes, resolve a small dependency chain and produce validated staging, without host installation or a package archive/database.
- Target native x86_64 Linux on NixOS first, with C and GCC/GNU Binutils. C++, other targets and production PackageKit/Pacman adapters are outside this first path.
- Prefer compatible validated installed host dependencies; build project recipes only when needed. Host-bound artifacts are allowed; portability, relocation and survival after host upgrades/removals are not promised.
- No bootstrap tool bundles or requirement to build a private compiler, glibc, libgcc or loader. Nix is only an installed-host provider, not a universal prerequisite.
- On implementation, create active catalog entries for `gcc`, `bash`, `coreutils` and `binutils`; materialize the approved OpenSSL example with its probe when that coverage is implemented. Documentation fixtures are not active entries.
- Start with local recipes at `recipes/<name>/KPB.recipe`, a small C shared library and a dependent C application. The demonstration uses one `libdemo.so` ELF with SONAME `libdemo.so`, avoiding versioned aliases, copied duplicate ELFs and an undeclared `ln` command. OpenSSL probing is optional when its actual inputs exist, not a forced demonstration dependency.

## Rust implementation

Use Rust 2024, minimum Rust 1.90, one Cargo package with a library and thin CLI. Use synchronous `std::process::Command` orchestration, one package build at a time, and cohesive domain/catalog/recipe/resolver/provider/probe/sandbox/source/artifact/manifest/CLI modules. Keep native commands, D-Bus and provider-specific IDs outside the resolver/domain layer. Do not add an async runtime, database or plugin system for this milestone.

Approved dependency families are `serde`, `toml`, `serde_json`, `sha2`, `tree-sitter`/`tree-sitter-bash`, and a small Unix binding such as `libc`. Commit compatible resolutions in `Cargo.lock`, disable unused features where practical and check minimum Rust and stable. An incompatibility requiring a new MSRV or unsafe substitute needs a decision. Archive libraries (`tar`, `flate2`, `lzma-rust2`) belong to the later D15 slice, not unused initial dependencies.

Parse complete recipes as syntax trees without running Bash. Reject error/missing AST nodes and unsupported forms; extract function spans from the AST, not brace counting. Serialize validated metadata safely into stage scripts, executed only inside Bubblewrap. Syntax parsing does not make function bodies trustworthy.

## Dependency planning

Resolve declared direct/transitive requirements, enabled test dependencies, executor requirements and probe prerequisites before obtaining package sources or running recipe functions. Validate ready host candidates; recipe-produced prerequisites may remain planned until built in dependency order. Never claim a pending probe passed. Reject cycles with a requiring chain.

If no compatible validated host component or satisfiable project recipe/artifact provides a requirement, stop before a partial recipe build. Report every known unresolved name, constraint, role, requiring chain and reason. Distinguish absence from unsupported/unavailable queries, ambiguity, conflict, integrity failure and unavailable isolation. Never install/repair host packages or fetch substitute tools automatically.

Select one version/provider per logical dependency; reject incompatible exact constraints without automatically building alternatives. Preserve direct/transitive and executor/validation/build/test/runtime roles, even when one component serves several roles.

Compose KPB artifacts from direct runtime/build requirements, enabled test requirements and their transitive runtime inputs. Do not propagate dependencies used only to build a completed dependency. Merge shared directories while retaining contributor ownership; reject file/link/type and mount-destination collisions, with no silent overwrite or shadowing. Host/KPB competing library identities remain D16: reject that composition until decided.

Previously produced artifacts are not a cross-run validated cache: revalidation applies, and persistent reuse/lifetime is D05. The post-link runtime refinement below supplements the pre-build plan; final ELF requirements are not all known before linking.

## Host providers and evidence

Use a provider-neutral `HostDependencyProvider` boundary for capabilities, ownership, package metadata, installed files, integrity checks and registered references. Results distinguish known, unsupported, unavailable, denied, missing, ambiguous, stale and integrity-mismatch states. Native identifiers remain opaque to the resolver. Host packages/files remain externally owned: KPB must not remove them when its own packages are removed, overwrite them without explicit authorization/safeguards, or modify the native package database. Provider references are evidence, not an automatic mount set or complete ABI closure.

Prefer PackageKit where its implemented backend queries supply the required evidence. Pacman/libalpm and Nix/NixOS are approved native directions when needed. The first complete implementation is NixOS/Nix; report other adapters as unimplemented, not as proven backend incapability. Additional backend/platform contracts are D09; Nix output-directory mounts must not become a universal provider representation.

A candidate requires:

1. Owning provider/package and canonical required files, including symlink/wrapper chains.
2. Compatible effective tool version/target, or library headers/link/runtime files and architecture/ABI evidence. Preserve native package versions separately; never infer equivalent names/versions across distributions or invent metadata from filenames.
3. Offered integrity checks with method, coverage and outcome. Record unsupported checking explicitly; it alone does not reject a candidate whose other checks pass. A failed/denied/inconclusive offered check is not unsupported. Actual mismatches reject the candidate even when it runs.
4. A passing isolated functional probe using the selected resources.

Unify consistent evidence only for the same canonical component/file set and compatible version/target, retaining all origins. For multi-command tools, compare the complete set. Distinct equally valid candidates require explicit selection; no PATH/root/catalog order or highest-version tie-breaker. Report contradictions; neither fallback nor user choice waives validation or hides integrity failures. Invalid catalog data is an error, not missing dependency fallback.

## Nix discovery and trusted orchestration

Use only existing roots: `/run/current-system/sw`, the current user's `$HOME/.nix-profile` alias when present, and additional registered profile/store-output directories explicitly passed with `--nix-root`. Resolve/deduplicate canonical roots. Do not inspect other users' profiles or accept arbitrary directories, derivation files, expressions or flake references.

Enumerate tool candidates only via declared names in each root's `bin/`. Resolve owned symlinks/wrappers and use registered references to complete that candidate's execution resources, not to enumerate transitive competing tools. Do not derive roots from user PATH. A multi-executable candidate is the complete compatible entry-point set from one root, even when its files belong to several outputs; reject incomplete sets. Library discovery follows declared header/link/runtime requirements across compatible outputs in selected roots/references.

Queries use the explicit trusted Nix CLI and local daemon store, offline and read-only, with offered content verification. No global store scan, nixpkgs evaluation, download, profile change or automatic missing-output installation. Record missing metadata/capabilities truthfully. Registered hashes/content verification do not imply signature trust. Do not mount the whole profile/reference closure merely because it was discovered.

`--bwrap PATH` and `--nix-cli PATH` select absolute executable paths, never command strings. NixOS defaults are `/run/current-system/sw/bin/bwrap` and `/run/current-system/sw/bin/nix`. Missing defaults require an explicit path; do not search PATH/store for substitutes. Resolve and record canonical identity/content evidence and effective capabilities. Operator selection establishes a trusted control-plane input, not proof of authenticity.

Record KPB and its own runtime as trusted orchestration inputs; do not recursively validate KPB through its resolver. Only necessary helper resources enter isolated helper mount plans. Provider CLI/daemon sockets never enter recipe sandboxes.

## Probe registry and command roles

Use a compiled-in Rust registry containing ID, supported kind, typed parameters/defaults, auxiliary requirements and implementation. Catalogs select probes without code or overridden auxiliaries. Version IDs when evidence semantics change.

| Probe | Parameters/defaults | Required operation |
|---|---|---|
| `gcc-tool-v1` | `language="c"`, `target="native"`; only these values. | Owned GNU GCC/version/native target, then compile, link, inspect and execute a KPB-owned C fixture. Validate assembler/linker and execution resources; reject missing startup files/nonfunctional wrappers. Use the candidate, not another GCC. |
| `bash-tool-v1` | None. | Owned Bash/version/options with startup files disabled. |
| `coreutils-tool-v1` | None. | Owned GNU `mkdir`/`install`, raw banners and effective versions. |
| `binutils-tool-v1` | None. | Owned GNU assembler/linker/readelf, versions and native target support. |
| `openssl-shared-c-v1` | `linkage="shared"`; only this value. | Auxiliary validated `gcc` and `binutils`; compile/link/run KPB-owned SSL+crypto API fixture, compare header/runtime versions and inspect loaded identities, without network. |
| `curl-tool-v1` | None; later D14 slice. | Owned curl/version/HTTPS capability with separately approved CA resource; no inherited configuration. |

Probe-specific version parsing retains raw and interpreted versions. Exact upstream comparison follows the recipe contract; package revisions/epochs are separate. Probes are bounded checks, not proof of every operation or ABI.

Resolve probe auxiliary edges before the consumer, using validated host/recipe inputs. `--skip-checks` never skips probes. A selected tool's owned runtime is its explicit execution closure, not recursively invented logical library/compiler probes; separately declared library requirements still need their probes.

KPB owns Bash stage-launch and Binutils/readelf inspection edges. Recipe-used `mkdir`/`install` require explicit `makedepends=('coreutils')`; never infer command use from Bash bodies or grant the entire registry. Rust filesystem operations do not require coreutils. The initial runnable tool coverage does not assume Make, CMake, sed, grep, ln or `/bin/sh`; an additional interpreter contract requires a decision.

## Prefix, environment and workspace

KPB dependencies are read-only at `/opt/kpb` inside the sandbox. Recipes receive `prefix=/opt/kpb`; only `$pkgdir/opt/kpb` is package payload. Keep current staging separate from its own dependency tree. This authorizes no creation/population of host `/opt/kpb`; artifacts are prefix-bound.

| Environment | Policy |
|---|---|
| `PATH` | `/opt/kpb/bin`, then read-only `/tools/bin` aliases for selected validated host commands. |
| `PKG_CONFIG_LIBDIR` | `/opt/kpb/lib/pkgconfig:/opt/kpb/share/pkgconfig`, plus only selected validated host metadata locations. |
| `PKG_CONFIG_PATH` | Unset. |
| `CMAKE_PREFIX_PATH` | `/opt/kpb`, plus only selected validated host search locations. |
| Compiler/linker flags | No inherited user flags or globally injected flags; recipe adjustments explicit. |
| Compiler search overrides | Clear inherited `CPATH`, `C_INCLUDE_PATH`, `CPLUS_INCLUDE_PATH`, `COMPILER_PATH`, `LIBRARY_PATH`, `GCC_EXEC_PREFIX`. |
| `LD_LIBRARY_PATH`, `LD_PRELOAD` | Unset; no inherited or automatic loader overrides. Any recipe-specific adjustment must be explicit and validated. |
| Private shell environment | `HOME=/tmp/home`, `TMPDIR=/tmp`, `LC_ALL=C`; no inherited user/session environment. |

Compiler/wrapper defaults may contribute flags; record the selected tool and resulting ELF. Discovery variables do not authorize exposing implicit host dependencies. Read-only package roots may contain additional commands: PATH selection is not an executable allowlist.

## Bubblewrap and resource limits

Require user/mount/PID/network/IPC/UTS separation, nonroot execution, cleared environment, dropped capabilities, new session and death-with-parent supervision. No external network for recipe functions or probes. Stop on insufficient effective isolation; no unprotected fallback.

Mount approved dependency/tool files or recorded output roots read-only at required canonical paths, private recipe/input snapshots, minimal read-only `/proc` and `/dev`, private temporary space and stage workspaces. Exclude host root, whole `/usr`/`/lib`/store/profile trees, home contents, credentials, session and provider sockets. Source snapshots are immutable; private working copies may be writable. Validate symlinks/overlaps and never mount a writable parent alias defeating a read-only child.

| Phase | Private source/build workspace | Current staging |
|---|---|---|
| Prepare, build, check | Writable. | Not writable. |
| Package | Writable for bookkeeping/relinking. | Writable; only staging is package output. |
| Artifact inspection/probes | Required inputs read-only; private probe scratch writable. | Read-only when inspecting an artifact. |

| Limit | Approved default and scope |
|---|---|
| Phase / whole invocation wall time | 1,800 / 7,200 seconds. |
| Tool / library probe wall time | 30 / 120 seconds. |
| CPU | 600 seconds per process (`RLIMIT_CPU`). |
| Address space | 4 GiB per process (`RLIMIT_AS`). |
| Regular file size | 2 GiB per file (`RLIMIT_FSIZE`). |
| File descriptors / core dump | 1,024 per process / zero bytes. |
| Private temporary filesystem | 512 MiB. |
| Later download/extraction admission | 1 GiB/source; 4 GiB expanded regular files and 200,000 archive entries/build, subject to D14/D15. |

`--limit NAME=VALUE` accepts a fixed positive-numeric allowlist; reject unknown/invalid/unenforceable limits and record effective values. No override disables isolation. Enforce compatible hard/soft limits and wall-time descendant cleanup; test spawning/reparenting/termination-resistant children before claiming cleanup.

No aggregate build CPU/memory/process/disk quota or complete denial-of-service protection is promised. `RLIMIT_NPROC` accounts for a real UID, not one build. Multi-user services, parallel package scheduling and aggregate quotas require D08.

## Sources and execution coverage

The recipe format permits HTTPS and local sources, but initial `plan`/`build` support verified ordinary local files only. Reject HTTPS and local basenames ending case-sensitively in `.tar`, `.tar.gz` or `.tar.xz` with an unsupported-feature diagnostic. Other suffixes remain hashed ordinary data, without archive guessing or implicit decompression. Static `validate` may accept overall format syntax while separately reporting execution coverage.

HTTPS execution requires D14; the approved direction is validated preinstalled curl outside recipe execution, disabled user config, HTTPS-only redirects, normal certificate checks and explicit approved CA resources. Clear inherited proxy/curl/loader settings; no tool/certificate downloads or trust changes. Acquisition follows satisfiable planning and size/time/hash checks.

Archive execution requires D15. The approved direction is an isolated resource-limited worker; validate paths/link targets/types/cross-source collisions and enforce expansion/count limits while reading. Reject special files and escapes, never follow archive-created links outside `srcdir`. Libraries do not replace containment checks. No untrusted decoding runs with home access or writable host inputs.

## Static artifact acceptance

Apply validation to every regular staged ELF, regardless of recipe identity. Detect ELF by contents, including DSOs without executable mode. Reject staged regular files ending case-sensitively in `.a`, and files with ordinary/thin ar archive magic regardless of name, as unsupported static-library artifacts. This excludes ar data containers too, but does not prohibit approved external link-input archives or change source-suffix rules. Broader static-library support remains D07. Initial supported ELF kinds are native x86_64 executables/DSOs; reject other executable formats/kinds, privileged bits, special files, unresolved/unapproved links and runtime requirements. Ordinary data/directories and supported symlinks retain validation; broader executable/runtime formats require D07.

Use validated `readelf` inside isolation. Inspect interpreters, recursive `NEEDED` resolution, RUNPATH, architecture and declared compatibility. Planning establishes eligible verified resources; post-link refinement validates the actual runtime subset and records separate edges. Newly derived host runtime files must be in the verified compiler reference set, with ownership/compatibility evidence; membership alone is insufficient. Requirements outside eligible inputs stop acceptance and require a new plan.

Require an unambiguously associated linker map for each regular ELF at `$builddir/kpb-link-maps/<path-relative-to-pkgdir>.map`, preserving directories. No new recipe field; the recipe supplies the file by convention. Aliases to the same staged ELF need no duplicate map. Validate map paths/association and copy/hash evidence. Association checks the conventional staged path and the map's link-output name against recorded build evidence. A map does not cryptographically bind its records to the staged ELF contents; hashing both preserves the observed files but does not prove that correspondence. Do not claim stronger provenance. Missing, ambiguous or unsupported map records reject acceptance.

Maps describe link-time inputs, not runtime mounts. Distinguish verified external archives/objects, link-time shared objects and compiler-generated private intermediates. Record producing stage/tool evidence for transient objects; do not require hashes after their removal or infer provenance from `/tmp` alone. Reject references outside approved inputs/private execution workspaces. This evidence is not a universal static-origin or semantic-safety proof.

Recipes explicitly request and verify RUNPATH `/opt/kpb/lib` where needed, with appropriate new-dtags options. Record wrapper-added paths. An unused directory is allowed only within already verified read-only approved inputs, as search exposure rather than an automatic runtime mount. Reject unknown/writable/escaping paths, including `/tmp/evil`; never rewrite ELF silently. RUNPATH alone does not resolve every transitive dependency or authorize inherited loader caches/configuration.

`kpb build` accepts staging statically; it does not execute produced programs. Recipe `check()` and dependency probes keep their execution contracts. A project integration test runs the known C fixture in a second runtime-only Bubblewrap, with fixed executable/arguments, expected exit/output (`demo=42`), timeout, no build tools, inherited loader variables or network. Its result is separate from static package acceptance; no generic `run`, output-execution metadata or callback is approved.

## Per-run evidence

Create fresh private run evidence at the [project-layout default](#local-project-layout), or a new child of explicit `--work-root`. JSON records use `schema_version=1` for plan, probes, commands, phases, artifact inspection and final manifest. This is not installed state or a reusable validation cache.

Record KPB/catalog/probe identity, recipe/input/source hashes, selected providers/candidate sets/roles, ownership/origins, package/raw/effective versions, canonical paths, integrity method/coverage/results, runtime/target compatibility, linker maps, mounts/environment/limits, argv, skipped tests and failures. Snapshot/hash recipe and declared inputs before use. Content identity is primary; existing Git revision/dirty status is supplementary, without requiring Git or remote checkout.

Re-discover/revalidate each invocation and recheck profile/registered identities, selected digests/offered verification and prerequisites before dependent phases/probes and final acceptance. Changed/disappeared inputs stop the run for a new plan; never silently substitute or reuse old success. This is not an atomic snapshot or GC-retention guarantee (D05/D06). Failed/interrupted staging remains invalid with diagnostic evidence, never a success manifest.

## Local project layout

For `validate`, `plan` and `build`, positional `PATH` is an existing recipe directory `<root>/recipes/<name>`, not executable-search PATH or a recipe file. Resolve relative arguments against the invocation directory, canonicalize, require the literal `recipes` parent and `<name> == pkgname`. Derive `<root>` as that parent's parent, without Git/CWD/upward-search heuristics. Dependency recipe directory names must match their `pkgname` too.

| Resource | Location |
|---|---|
| Requested recipe | `<root>/recipes/<name>/KPB.recipe`. |
| Recipe dependency | `<root>/recipes/<dependency>/KPB.recipe`. |
| Entire catalog | `<root>/catalog/dependencies`. |
| Default run evidence | `<root>/.local/runs/<run-id>/`. |

`--work-root` overrides only the run parent, not recipe/catalog lookup. All three commands validate every catalog entry before planning; malformed unrelated entries are errors. `validate` makes no provider queries, runs no probes, acquires no sources and performs no writes, including run-directory creation. Missing/invalid layout or catalog produces an actionable error; there is no embedded-catalog fallback. Standalone recipe files, arbitrary layouts and installed catalog lookup are outside this slice.

## CLI

| Command/option | Contract |
|---|---|
| `kpb validate PATH` | Validate local recipe/catalog as data; no source acquisition or recipe/probe execution. |
| `kpb plan PATH` | Plan the full graph, inspect host evidence, run ready isolated probes; list planned recipes and explicitly pending recipe-dependent probes. No recipe execution. |
| `kpb build PATH` | Preflight, acquire supported sources, execute dependency/probe/build vertices in order, statically validate staging and print run/output location. No installation. |
| `--select LOGICAL=ID` | Repeatable explicit choice among opaque candidate-set IDs; recompute evidence and reject stale/invalid selections. No persistence or waived checks. |
| `--skip-checks` | Skip recipe `check()` and test-only dependency resolution; never dependency probes. |
| `--nix-root PATH` | Additional existing installed root under the discovery rules. |
| `--bwrap PATH`, `--nix-cli PATH` | Absolute trusted orchestration executables under the fixed-default rules. |
| `--work-root DIR` | Parent of a fresh private run directory. |
| `--limit NAME=VALUE` | Fixed positive numeric resource-policy overrides. |

Initial CLI is non-interactive: ambiguity prints candidates and stops without a valid explicit selection. No arbitrary command/environment inheritance, provider expression, configurable prefix or isolation-disable option. Diagnostics identify requirement, role, chain, relevant file/field, evidence/candidates and remedy; JSON records carry typed reasons. Exit statuses: `0` success, `2` invalid CLI, `1` operation failure, `130` interruption. Exact prose is not a public compatibility promise.

## Approval reference map

Legacy IDs remain usable when reviewing earlier discussions; their rules are incorporated here.

| Earlier approval | Current owning section/document |
|---|---|
| P01 | [Catalog schema](dependency-catalog.md). |
| P02 | [Rust implementation](#rust-implementation). |
| P03, A02, A04, B03 | [Probes and roles](#probe-registry-and-command-roles); [discovery](#nix-discovery-and-trusted-orchestration). |
| P04, A01, A06 | [Host evidence](#host-providers-and-evidence); [discovery](#nix-discovery-and-trusted-orchestration). |
| P05, A03 | [Environment](#prefix-environment-and-workspace); [isolation](#bubblewrap-and-resource-limits). |
| P06, A05, B01, B02 | [Acceptance](#static-artifact-acceptance); [evidence](#per-run-evidence). |
| P07 | [CLI](#cli). |
| C01 | [Local project layout](#local-project-layout). |
| C02 | [Recipe version grammar](recipes.md#fields). |
| C03 | [Static artifact acceptance](#static-artifact-acceptance). |
| P08, A07, B03 | [Milestone](#initial-milestone); [source coverage](#sources-and-execution-coverage). |

