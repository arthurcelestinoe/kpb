# Controlled reuse of host build tools

## Status

The maintainer approved controlled reuse of installed host dependencies and acceptance of host-bound runtime artifacts for the initial milestone. The objective is working applications with as little compilation as necessary. Reuse compatible validated available components, build project recipes only for unsatisfied requirements, and stop with an actionable dependency report when no valid host component or buildable recipe/artifact can satisfy a requirement.

Bubblewrap isolation remains mandatory. PackageKit is preferred where its backend supplies sufficient evidence, with Pacman/libalpm and Nix/NixOS providers where needed. Nix is a host provider for existing installed components, not a global requirement or a source of automatically downloaded tools. This policy does not require rebuilding a private toolchain or runtime.

The general resolver, provider interface, recipe executor, and final package validator remain unimplemented. The Nix-specific probe below is a trusted experiment, not a production native adapter or blanket permission for additional native adapters. The approved recipe syntax is unchanged; see [the build contract](build-environment.md) for dependency selection, missing-requirement handling, and runtime validation.

The question is whether an existing tool can be identified, checked, and used in Bubblewrap without rebuilding infrastructure or exposing the host filesystem indiscriminately. The local experiment answers this for one installed GCC on NixOS. It does not establish equivalent coverage on Arch, Debian, Fedora, or another backend.

## Separate discovery, evidence, and authorization

PATH supplies candidates, not evidence that a requirement is satisfied. Preserve the discovery path and resolve the executable; identify the owners of both the entry point and the underlying executable. Alternatives, symlinks, compiler caches, scripts, and wrappers can cross package boundaries. A generic implementation must account for their chain, not assume a single package owns every component.

Keep these facts separate:

- Provider-scoped package identity and installed package version, including native revision/epoch where present.
- Effective tool family/version and target, probed inside isolation after ownership and available integrity checks.
- File membership according to the package manager.
- Content integrity against package-manager records, with the exact verification strength recorded.
- The additional executable, interpreter, library, headers, linker, plugin, specs, and data paths needed for the intended operation.

Ownership and an intact file do not prove that a tool is safe, compatible with every recipe, or sufficient to compile/link. Tool probes and builds still need isolation. Do not execute an arbitrary PATH candidate merely to ask its version before identifying it.

## Approved dependency naming and mapping

Recipes declare stable KPB dependency names such as `gcc`, `make`, and `openssl`. These names belong to KPB's dependency namespace; recipes do not embed distribution-specific package identifiers or change their dependency names for each host.

Each host provider maintains explicit mappings from those names to candidate installed packages and the files/components needed to satisfy the requirement. A logical dependency may require multiple native packages, for example separate development headers and runtime libraries. Native names or matching version strings alone never establish that the requirement is satisfied; do not guess a mapping merely because names resemble each other.

Validation depends on the component:

- For tools, establish ownership and available integrity evidence, then verify the effective tool family, version, target, and required execution components inside isolation. Keep native package versions separate from effective tool versions.
- For libraries, establish the required development headers, link-time files, runtime libraries/loader relationships, and relevant architecture/ABI compatibility. A runtime library installed without required development files does not satisfy a build requirement.

Without an explicit mapping or sufficient evidence, the host candidate does not resolve the dependency. Use an available validated KPB artifact or build the corresponding project recipe when its full graph is satisfiable; otherwise stop and report the unresolved requirement and why the host candidate could not be used. Keep integrity failures and conflicting evidence visible rather than hiding them through a silent substitution.

This naming/mapping model is approved. The [catalog structure](dependency-catalog.md) is also approved: project-maintained TOML, one logical dependency per file under `catalog/dependencies/`, versioned with KPB. Entries classify tools/libraries, hold explicit provider mappings and required components, and reference KPB-implemented probes by identifier rather than arbitrary commands. Machine-specific paths, observed versions, and results remain local. Initially there are no external catalogs or automatic mapping updates. The detailed schema, concrete entries, loader, and provider implementation remain pending. The existing bare-name/exact-upstream-version recipe syntax is unchanged; this does not add virtual-provider syntax or a universal native-version comparator.

## Provider and candidate selection

Nix catalog mappings use [installed-component discovery](dependency-catalog.md#nix-installed-component-discovery) within explicitly selected installed profiles/system roots and their registered references, rather than conventional package-name lists. This does not authorize evaluating nixpkgs, fetching missing components, scanning the entire store, or bypassing the evidence and selection policy below. The mode is approved but its general implementation is pending.

The maintainer approved the following initial policy:

1. Prefer PackageKit when its installed backend supplies the minimum evidence required for the operation.
2. Use an approved native provider when PackageKit is absent or lacks a required capability. This is capability-based fallback, not permission to bypass a failed integrity check or conflicting evidence.
3. If providers identify the same component and the same canonical files, unify consistent evidence while preserving each provider's identity, package records, methods, and results. Similar names or version strings alone do not establish equivalence, and native package versions must not be confused with effective tool versions.
4. If multiple distinct components are equally valid for the requirement, stop and present the candidates for explicit selection. Do not select by PATH order, catalog order, or highest version. Provider preference does not authorize arbitrary selection between distinct equally valid components.
5. If evidence contradicts, report the conflict instead of silently preferring whichever result permits the build. Evidence unification must not erase a failed check or disagreement.

An explicit user choice may select a candidate, but cannot waive the required ownership, compatibility, integrity, functional probe, or Bubblewrap checks. The selected dependency must still satisfy the recipe constraints and the full graph. An invalid candidate cannot be made valid by user preference; unresolved requirements follow the existing artifact/recipe fallback or stop policy.

This policy is separate from [mapping applicability and specificity](dependency-catalog.md#host-mapping-selectors). It does not resolve equally specific ambiguous catalog mappings or make a provider available merely because a mapping names it. The selection interface, how choices are recorded/reused, and the concrete evidence-equivalence algorithm remain unimplemented and require further design.

## Minimum host dependency evidence

The catalog's [approved host selectors](dependency-catalog.md#host-mapping-selectors) determine mapping applicability within a provider using exact distribution `ID`, optional release `VERSION_ID`, and KPB architecture names. A matching release-specific mapping overrides a generic mapping, equal-specificity matches are ambiguous, and `ID_LIKE` does not provide automatic derivative fallback. These selectors do not replace component validation or decide precedence between providers.

The maintainer approved the following minimum for accepting a host candidate:

1. Identify its owning package/provider and the required canonical files/components. A name found in PATH is not sufficient.
2. Establish compatibility: effective version and architecture/target for tools; required headers, link-time files, runtime components, and relevant compatibility for libraries. Keep package versions separate from effective component versions.
3. Run the integrity checks offered by the provider and record their scope and result. If the provider does not offer an applicable integrity check, explicitly record that limitation; do not claim verified contents. This unsupported capability alone does not reject a candidate whose other required evidence and sandbox probe pass. A failed offered check, denied access, or unavailable verification data is not equivalent to an unsupported capability and must not be silently bypassed. An actual integrity mismatch rejects the candidate, even if it runs successfully.
4. Pass a minimal functional probe inside Bubblewrap: execute the tool and validate the required identity/version behavior, or compile, link, and execute a small program using the selected library headers, link-time files, and runtime. Use only the explicitly selected components and the required isolation boundary.

Record the probe, selected inputs, result, and any unsupported integrity checks with the dependency evidence. A probe is necessary evidence for the selected operation, not a complete test suite or proof of all ABI compatibility, safety, or portability. Concrete probe templates, detailed ABI checks, and provider-specific integrity coverage remain implementation decisions.

Auxiliary tools needed by probes are declared by KPB's [probe registry](dependency-catalog.md#auxiliary-tools-belong-to-the-probe-registry). The resolver must resolve and validate them before executing the dependent probe. Catalog entries reference the probe and its accepted parameters without duplicating these internal tool requirements; unresolved auxiliary requirements follow the existing report-and-stop policy and do not authorize skipping validation.

Insufficient evidence or a failed probe leaves the host dependency unresolved. Reject candidates with integrity mismatches and report why they cannot be used. Resolve through an available validated KPB artifact or a project recipe whose full graph is satisfiable; without such a solution, stop and report the dependency. Do not automatically repair or install host packages, suppress a failed check, or weaken Bubblewrap to obtain a passing result.

These are approved requirements for the future resolver/providers, not implemented general validation. The existing NixOS GCC experiment covers one tool case and does not implement library probes or unsupported-integrity handling across providers.

## Proposed minimum provider boundary

The following is a design sketch, not an implemented Rust trait or public API. Keep provider-specific IDs opaque to the resolver and keep D-Bus/native commands inside adapters.

```text
HostDependencyProvider
    capabilities()                 -> CapabilitySet
    owners(absolute_path)          -> Evidence<List<Ownership>>
    package(provider_package_id)   -> Evidence<PackageRecord>
    files(provider_package_id)     -> Evidence<List<FileRecord>>
    verify(file_records)           -> Evidence<IntegrityRecord>
    references(provider_package_id)-> Evidence<List<ProviderPackageId>>
```

`PackageRecord` carries provider identity, native package ID, optional package name/version/architecture, and evidence provenance. `Ownership` connects the requested path, canonical file, and provider package ID; it must permit multiple results. `IntegrityRecord` identifies checked files/content roots, method, hashes where available, observation time, and result. Provider references describe declared metadata relationships; they are not automatically the complete executable or ABI closure.

An `Evidence<T>` result distinguishes a known value from unsupported capability, unavailable data, denied access, missing package, ambiguity, stale observations, and integrity mismatch. Unsupported verification must not become “verified,” nor should missing version metadata be invented from a filename. Apply the [approved evidence minimum](#minimum-host-dependency-evidence): a recorded unsupported integrity capability differs from a failed or inconclusive offered check. The Nix experiment requires registered ownership and successful content verification because that provider offers the check.

A separate tool inspector compares the effective version/target with an explicit tool request and prepares a `MountPlan`. Each entry records the source/destination, owner, identity/hash evidence, read-only mode, and reason for exposure. The build executor applies the plan; providers do not mount directories or install packages. The resolver decides requirements using KPB's internal representation. A disagreement between providers requires diagnosis, not a silent choice of whichever answer permits the build.

The interface sketch does not yet implement the approved logical-name mappings or extend recipe version syntax. Providers must relate native package evidence to the requested component and its upstream version explicitly. Exact tool-version comparison is sufficient for the local probe; a universal cross-provider version comparator is not proposed.

## Provider feasibility

| Provider | Useful evidence | Limits requiring explicit handling |
|---|---|---|
| PackageKit | Installed package queries, `SearchFiles` with an absolute path and installed filter, `GetFiles`, package IDs/details, and dependency queries where supported. | Inspect the installed daemon/backend capabilities and actual results. Ownership/file lists do not establish file content integrity or the complete toolchain closure. Unsupported roles and ambiguous results need explicit outcomes. |
| Pacman/libalpm | Local `pacman -Qo` ownership, `-Q` installed versions, `-Ql` files, and local package dependency metadata. | Installed packages originally built from AUR can appear in the local database; `-Qm` only identifies packages absent from sync databases, not proof of AUR origin. `-Qkk` checks mtree-backed attributes where available; do not label it cryptographic content verification. Tool internals and target/runtime compatibility need additional inspection. |
| Nix/NixOS | Canonical registered store outputs, reference closure, NAR hashes, optional derivation metadata, and content verification. | A store basename is not authoritative name/version metadata. Derivations/profile manifests may be absent. Reference closures can include more files than the tool actually needs. Registration/content hashes are distinct from signature trust. |

Sources: [PackageKit transaction documentation](https://www.freedesktop.org/software/PackageKit/doc/dbus-org.freedesktop.packagekit1.Transaction.html), [PackageKit concepts](https://packagekit.freedesktop.org/doc/concepts.html), [Pacman manual](https://man.archlinux.org/man/pacman.8.en), [Nix path-info](https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-path-info), and [Nix store verify](https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-store-verify). These describe possible capabilities, not a claim that every installed version/backend implements them. The probe uses only the installed Nix CLI and existing local store outputs, without evaluating a moving nixpkgs source.

## Local experiment

The trusted harness is [experiments/host-tools/nix-gcc-probe.py](../experiments/host-tools/nix-gcc-probe.py), with a Bash payload and small C fixture. Python is orchestration for this experiment; Rust remains KPB's selected implementation language.

The probe finds GCC through PATH, resolves its path, requires a locally registered Nix GCC wrapper output, checks its explicit `orig-cc` relationship, obtains the local recursive reference closure, and verifies its contents with `nix store verify --store daemon --offline --no-trust --recursive`. This checks registered NAR contents; signature trust is deliberately not claimed. The preinstalled Nix CLI is an explicit trusted orchestration input (defaulting to `/run/current-system/sw/bin/nix` on NixOS), not another candidate selected through PATH. Queries explicitly use the local daemon store rather than an inherited remote store. Python, Bubblewrap, the provider CLI, and the host package database remain the experiment's trusted foundation; their authenticity is outside this probe's validation scope. No candidate version command runs before ownership/content checks. Missing/ambiguous helpers or unsupported ownership stop the probe.

The manifest records the original and canonical executable paths, executable hash, package/output identity, available version metadata, expected/effective tool version, target, package references/NAR hashes, mounted roots, source payload hashes, and result. It does not execute recipes or make packages eligible for installation. `--run` explicitly selects sandbox execution; without it the probe prepares only the verified plan.

Bubblewrap mounts individual verified store output directories read-only, a small explicit tool directory, read-only payloads, private `/tmp`, minimal read-only `/proc` and `/dev`, and one writable workspace. It does not mount `/usr`, `/run`, user home/profile directories, the host store as a whole, the Nix CLI/socket, or the host loader cache. It clears the environment, drops capabilities, creates new user/mount/PID/network/IPC/UTS namespaces and a new session, and stops on setup failure. The selected GCC wrapper still has access to other executables within its approved package closures: this is not a command-execution allowlist or a completed production sandbox policy.

The payload checks namespace changes, nonroot identity, capabilities, `NoNewPrivs`, read-only mounts, hidden host paths, cleared compiler/session variables, and unreachable external networking. It checks the exact effective GCC version, compiles a C object including host development headers, links a small executable, inspects ELF metadata, and runs the fixture. The parent rechecks executable identity and registered closure hashes afterward. These observations are not an atomic host snapshot or a guarantee against concurrent root changes, package upgrades, or garbage collection; a production snapshot/lifetime strategy remains open.

### Executed results on 2026-11-07

| Observation | Result |
|---|---|
| Host | NixOS; native x86_64 Linux. |
| Discovery path | `/run/current-system/sw/bin/gcc`. |
| Registered owner | `/nix/store/r5ri78axx1qggkjq3vawywlzglg70b5w-gcc-wrapper-16.2.0`. |
| Real compiler output | `/nix/store/xpaz3fi6ibqxb9sla4gjlp0c82v566y8-gcc-16.2.0`. |
| Effective tool version/target | `16.2.0`, `x86_64-unknown-linux-gnu`. |
| Structured package version | Unavailable: the local derivation was absent. The store name was retained as an identity/hint, not parsed as authoritative version metadata. |
| Verified reference closure | 27 existing output directories; 406,737,104 NAR bytes (about 388 MiB), mounted without copying their contents. |
| Integrity and isolation checks | Passed for the recorded closure and fixture. |
| Compile/link/execute | Passed; program reported host glibc `2.44`. |
| Unowned PATH shadow | Rejected before running the candidate or creating the experiment output directory. |
| Incompatible requested version `999.0.0` | Rejected before compilation, with required/actual versions in the log; no object or executable produced. |
| Provider CLI shadow / inherited `NIX_REMOTE` | A fake `nix` on PATH was not executed; an inherited nonexistent remote socket did not replace the explicit system CLI/local daemon. The experiment still passed. |
| Missing host-tool candidate | The probe named the unavailable command and stopped before creating its workspace or executing any fixture. This is not a test of the future general recipe resolver. |
| Runtime policy | Validated host/Nix runtime dependencies are permitted. The fixture is not a complete package, and the probe does not implement final package acceptance. |

The ELF interpreter points into the registered host glibc output, and RUNPATH includes host glibc/GCC library outputs. This is direct evidence that reusing a compiler with its default settings can also select host target-runtime components. A matching compiler version does not establish an independent or cross-distribution portable result.

The successful rerun under the approved policy is in `/tmp/kpb-host-policy-accepted/`; its manifest records `host_runtime_allowed=true`. It retains `package_accepted=false` because the fixture is not a complete package and the probe is not a package validator. The intentional version failure is in `/tmp/kpb-host-tool-local-mismatch/`; the provider-selection isolation test is in `/tmp/kpb-host-tool-provider-isolation/`. These are disposable local experiment outputs, not committed package artifacts. No host packages were installed, removed, repaired, or rebuilt, and no profile, shell configuration, or package database was changed by this experiment. No glibc/toolchain source compilation or tool download was needed for the host-tool probe. The small fixture is not a comparative benchmark of complete KPB package builds.

### Reproduction

Require already installed Nix, Python 3.11+ with the standard library, GCC exposed through PATH, and Bubblewrap. The helper executables must be unambiguous members of the compiler's registered closure. The probe is Nix GCC-wrapper-specific and fails on an unsupported layout; it does not install missing components or fall back to arbitrary host paths.

```sh
/path/to/python3 experiments/host-tools/nix-gcc-probe.py \
  --expected-version 16.2.0 --bwrap /absolute/path/to/bwrap \
  --workdir /tmp/kpb-host-tool-new --run
```

Use a new work directory. The installed tool may differ on another host; choose the explicit expected version accordingly rather than silently accepting any discovered version. Keep manifests/logs for review. A failed probe does not relax isolation or authorize installing a dependency.

## Conclusions and decisions still needed

Controlled host-tool reuse is experimentally viable on this NixOS host, using already available components and a bounded read-only filesystem exposure. That can avoid provisioning another compiler for this case. PackageKit and Pacman/libalpm were researched but not executed here; their ownership, integrity, wrapper, and filesystem closure behavior still require experiments on appropriate systems.

Tool execution runtime and final package runtime remain different responsibilities, but both may use explicitly selected compatible host components. Host-bound artifact acceptance is now approved. A compiler's availability still does not automatically declare every library it may select as a target runtime dependency: identify, validate, and record those components before accepting an artifact.

Before production integration, decide concrete tool/library probe templates and detailed ABI checks; provider-specific integrity coverage and capability detection; the detailed TOML catalog schema and concrete provider entries; lifetime/snapshot strategy; minimum supported daemon/CLI versions; resource limits and finer mount exposure; artifact compatibility labels; and cache invalidation. Host headers/libraries must be explicitly selected and validated. Reproducibility records should include exact component identities/hashes, source inputs, flags, tool configuration, target/runtime identity, and controlled environment. A package version alone is insufficient, and native host runtime compatibility must not be advertised as cross-distribution portability.
