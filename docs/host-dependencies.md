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

An `Evidence<T>` result distinguishes a known value from unsupported capability, unavailable data, denied access, missing package, ambiguity, stale observations, and integrity mismatch. Unsupported verification must not become “verified,” nor should missing version metadata be invented from a filename. The production policy for accepting weaker evidence remains a maintainer decision; the Nix experiment requires registered ownership and successful content verification.

A separate tool inspector compares the effective version/target with an explicit tool request and prepares a `MountPlan`. Each entry records the source/destination, owner, identity/hash evidence, read-only mode, and reason for exposure. The build executor applies the plan; providers do not mount directories or install packages. The resolver decides requirements using KPB's internal representation. A disagreement between providers requires diagnosis, not a silent choice of whichever answer permits the build.

This proposal does not map recipe names to native package names or extend the approved recipe version syntax. Logical tool capabilities, distribution naming, native package versions, and upstream tool versions need explicit mapping. Exact tool-version comparison is sufficient for this probe; a universal cross-provider version comparator is not proposed.

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

Before production integration, decide the minimum acceptable evidence per capability; explicit logical-tool/package mappings; lifetime/snapshot strategy; minimum supported daemon/CLI versions; resource limits and finer mount exposure; artifact compatibility labels; and cache invalidation. Host headers/libraries must be explicitly selected and validated. Reproducibility records should include exact component identities/hashes, source inputs, flags, tool configuration, target/runtime identity, and controlled environment. A package version alone is insufficient, and native host runtime compatibility must not be advertised as cross-distribution portability.
