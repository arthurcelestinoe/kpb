# AGENTS.md

## Purpose

This document provides instructions for AI coding agents contributing to **Kobalt Package Builder (KPB)**.

KPB is an experimental source-based package manager that uses build recipes and Git repositories as recipe sources.

Agents must prioritize correctness, security, maintainability, and architectural consistency over rapid feature development.

## 1. General Principles

- Read `CONTEXT.md` before proposing or implementing significant changes.
- Respect the project's current architecture and development stage.
- Prefer small, focused, reviewable changes.
- Avoid unnecessary dependencies and abstractions.
- Do not introduce major architectural changes without explaining their implications.
- Do not assume that proposed features are already implemented.
- Treat the project as experimental, but write code with production-quality expectations.
- Human review remains the final authority for architectural and implementation decisions.

## 2. Project Scope

KPB aims to provide:

- Package installation, upgrades, and removal.
- Dependency resolution.
- Source-based package building using recipes.
- Package metadata and an installed-package database.
- Git-based recipe repositories.
- Integration with dependencies provided by the host distribution.
- Host package discovery primarily through PackageKit.

The initial milestone builds project-maintained recipes while reusing explicitly identified, compatible, validated host tools and dependencies to minimize compilation. Use project recipes for requirements the host cannot satisfy. Host-bound runtime artifacts are permitted; cross-distribution portability is not implied. If a requirement has no valid host provider or buildable recipe/artifact, stop and report it before recipe execution.

Rust is the selected implementation language. The first functional milestone is recipe validation, resolution of a small dependency chain, and artifact production in staging, without installation into the system. The Rust edition and toolchain are not yet selected.

Follow [docs/build-environment.md](docs/build-environment.md) for the fixed `/opt/kpb` prefix, per-build dependency tree, discovery settings, and Bubblewrap isolation direction. These are approved requirements, not implemented functionality or authorization to create or populate the host's `/opt/kpb`.

KPB is **not intended to become a Gentoo clone** or to rebuild the entire host distribution.

Avoid expanding the scope toward full distribution management unless explicitly requested.

## 3. Architecture

Maintain clear separation between the following responsibilities:

1. **Recipe management:** parsing, validation, repository synchronization, and source metadata.
2. **Dependency resolution:** dependency graphs, version constraints, conflicts, and providers.
3. **Build system:** source acquisition, verification, preparation, compilation, and staging.
4. **Package management:** installation, removal, upgrades, and ownership tracking.
5. **Package database:** persistent metadata, dependencies, installed files, and package state.
6. **Host integration:** discovering host-provided packages and capabilities through a provider abstraction.
7. **PackageKit adapter:** communicating with PackageKit through its D-Bus API.

Do not introduce unnecessary coupling between these components.

KPB's dependency resolver must remain independent from Nix, PackageKit, and individual native package managers.

### 3.1 Host dependencies and minimal compilation

- Prioritize functioning applications with minimal necessary compilation. Reuse compatible validated installed host components and available validated KPB artifacts; build project recipes only for unsatisfied requirements.
- Do not require building a private compiler, C library, runtime loader, or independent runtime to validate the first milestone.
- Identify the owning provider/package, canonical files, package metadata, effective tool version/target, integrity evidence where available, and required transitive components. PATH is a candidate discovery mechanism, not proof of ownership or compatibility.
- Apply [the approved evidence minimum](docs/host-dependencies.md#minimum-host-dependency-evidence): known ownership/files, compatible effective version/architecture or library development/runtime components, offered integrity checks, and a minimal functional probe in Bubblewrap. Explicitly record unsupported integrity checking; it is not verified content or a failed check. Actual integrity mismatches reject the candidate regardless of probe success. Insufficient evidence or failed probes require a validated artifact/buildable recipe or an actionable stop; never silently bypass offered checks or weaken isolation.
- Keep recipes and the resolver independent of providers. Never assume KPB recipe names, native package names, native package versions, and effective tool versions are interchangeable.
- Use stable KPB dependency names in recipes and explicit provider-maintained mappings to installed packages/files. Validate effective tool versions; for libraries validate headers, link-time files, runtime components, and ABI/architecture compatibility. Missing mappings or insufficient evidence leave the host requirement unresolved; use a validated artifact/buildable recipe or report it and stop. Follow [the approved mapping model](docs/host-dependencies.md#approved-dependency-naming-and-mapping).
- Follow [the approved catalog structure](docs/dependency-catalog.md): project-maintained TOML files under `catalog/dependencies/`, one logical dependency per file, versioned with KPB. Classify tools/libraries and declare provider mappings, required artifacts, and KPB-implemented probe identifiers. Keep observed machine paths/versions/results local; do not add arbitrary commands, external catalogs, or automatic mapping updates. The detailed schema, concrete entries, loader, and probe registry remain unimplemented.
- For Nix mappings, use [the approved representation](docs/dependency-catalog.md#nix-installed-component-discovery), `discovery = "installed-components"`, instead of `packages`, nixpkgs attributes, or shared machine-specific store paths. Search only explicitly selected installed profiles/system roots and their registered references; keep actual paths/hashes/origins local. Do not scan the whole store, evaluate nixpkgs, download/install missing outputs, or bypass validation. Exact discovery roots and general discovery remain unimplemented.
- Keep auxiliary tool requirements in the KPB probe registry, not individual catalog entries. Resolve and validate them before executing dependent probes; use validated host tools/artifacts or buildable project recipes, and report unresolved requirements and stop. Track their validation role separately from application runtime and recipe test dependencies. See [the approved responsibility split](docs/dependency-catalog.md#auxiliary-tools-belong-to-the-probe-registry); registry representation and compiler selection remain undecided.
- Apply [the approved host selectors](docs/dependency-catalog.md#host-mapping-selectors): exact `/etc/os-release` `ID`, optional exact `VERSION_ID`, and internal KPB architecture names translated by providers. Do not automatically use `ID_LIKE` or codenames as release substitutes. Within one provider/distribution/architecture, matching release-specific mappings override generic ones; equally specific matches require an ambiguity diagnostic. This does not decide precedence between providers.
- Apply [the approved provider/candidate policy](docs/host-dependencies.md#provider-and-candidate-selection): prefer PackageKit when it supplies the required evidence; use approved native providers when it is unavailable or lacks a necessary capability. Unify only consistent evidence for the same component/canonical files while preserving its origins. Stop and present distinct equally valid candidates for explicit choice; do not choose by PATH order or highest version. Report contradictory evidence, and never let provider fallback or user choice waive validation or hide an integrity failure. The selection interface and equivalence algorithm remain unimplemented.
- Resolve the complete selected graph before obtaining package sources or executing recipe functions. If any requirement lacks a compatible validated host component or buildable project recipe/artifact, stop and report the unresolved requirements, constraints, build/runtime/test roles, requiring packages/chains, and rejection or unavailability reasons. Distinguish unsupported queries from confirmed absence, and conflicts/integrity failures from ordinary missing packages.
- Do not automatically install host dependencies, fetch replacement tool bundles, change host profiles/shell configuration, or modify host package databases. Missing requirements must be explained to the user.
- Make approved host dependencies available read-only through an explicit Bubblewrap mount plan. Never inherit the user's PATH, compiler flags, loader environment, home, or session sockets into recipe execution.
- Accept validated host-bound artifacts, recording target/runtime compatibility and complete dependency provenance. An approved Nix/NixOS host runtime is permitted; a store path is not an automatic rejection reason. Do not claim relocation or cross-distribution portability.
- Preserve Bubblewrap as mandatory isolation. Stop if the required boundary is unavailable; provider discovery and host tool availability do not replace isolation.

Read [docs/host-dependencies.md](docs/host-dependencies.md) for the approved host dependency direction, proposed provider boundary, and experimental evidence. The NixOS GCC probe is a trusted experiment, not the Rust resolver, recipe executor, or final package acceptance implementation. Nix is required only for the Nix provider on hosts that use it; it is not a global project prerequisite.

## 4. Host Distribution Integration

### 4.1 PackageKit-first approach

**PackageKit is the preferred integration layer for querying packages provided by the host distribution.**

Host integration is part of the initial milestone. Prefer PackageKit where its backend provides the required evidence; keep unsupported capabilities explicit.

Agents should use PackageKit instead of implementing separate integrations for APT, DNF, Pacman, Zypper, and similar package managers whenever its supported capabilities satisfy KPB's requirements.

Host integration must use read-only operations, including:

- Querying installed packages.
- Resolving package names and identifiers.
- Inspecting versions and package metadata.
- Discovering package dependencies.
- Querying provided capabilities.
- Retrieving installed-file information when supported.

The exact supported operations depend on the PackageKit backend and must be verified.

### 4.2 Internal provider abstraction

PackageKit must not become a hard dependency of KPB's core architecture.

Implement host integration through a dedicated abstraction, conceptually named `HostDependencyProvider`.

This abstraction should:

- Expose host package information in KPB's internal representation.
- Separate host-specific logic from dependency resolution.
- Report unavailable or unsupported capabilities.
- Support additional provider implementations when necessary.
- Allow isolated testing without a running PackageKit daemon.

Do not couple the package resolver directly to D-Bus or PackageKit-specific package identifiers.

### 4.3 Native adapters

Direct native package manager adapters may be introduced when:

- PackageKit is unavailable.
- The required operation is unsupported by the installed backend.
- PackageKit cannot provide sufficient information for a particular dependency.
- A documented compatibility or performance limitation justifies a native implementation.

PackageKit, Pacman/libalpm, and Nix/NixOS are approved provider directions. Use Pacman/libalpm or Nix when needed for host ownership, integrity, or package-layout evidence; do not ask again for approval of this direction. Introducing other native adapters or changing provider policy requires maintainer approval.

Do not create parallel native integrations merely as a speculative optimization.

### 4.4 Ownership and safety

Agents must:

- Treat host-managed packages as externally owned resources.
- Never remove host-managed packages as part of KPB package removal.
- Never overwrite files owned by the host package manager without explicit authorization and safeguards.
- Avoid assuming that package names or versions are equivalent across distributions.
- Distinguish package metadata from actual library and ABI compatibility.
- Avoid modifying the host package database directly.

Automatic installation or removal of host-managed packages is outside the initial scope unless explicitly approved.

## 5. Dependency Resolution

KPB is responsible for resolving dependencies declared by its recipes.

Resolve initial dependencies through compatible validated host components and project recipes, minimizing builds. Complete the selected dependency graph before executing recipes; if no valid host component or buildable recipe/artifact satisfies a requirement, report it and stop. This includes transitive and enabled test dependencies.

Host-provided compilers, libraries, interpreters, and runtime loaders are permitted when identified, explicitly selected, and validated. Record effective tool and package versions separately, runtime compatibility, files, and provider ownership. Do not require an independently rebuilt C runtime or reject an artifact solely because its approved runtime comes from a Nix/NixOS host.

Compose validated KPB-managed dependencies into a read-only tree, with host components separately exposed through the explicit mount plan. Do not propagate dependencies used only to build a completed dependency. Allow one selected version per logical dependency; reject conflicting requirements and file/link/type collisions. Shared directories may merge while preserving contributor ownership. Keep current staging separate from dependency inputs.

PackageKit and other host providers supply evidence; they do not replace KPB's dependency resolver.

Agents must distinguish:

- KPB-managed dependencies.
- Host-provided dependencies.
- Build-time dependencies.
- Runtime dependencies.
- Direct and transitive dependencies.

Dependency relationships must preserve information about which package manager or provider owns each dependency.

Where feasible, record enough information to identify packages potentially affected by changes to host-provided libraries.

Do not assume that a package being installed means it satisfies every version, ABI, or build requirement.

## 6. Build Recipes

Read [docs/recipes.md](docs/recipes.md) before changing recipe parsing or execution. It specifies the approved initial `KPB.recipe` format: one package per file, restricted metadata followed by Bash functions, inspired by Arch PKGBUILDs and BSD ports. Do not assume compatibility with existing PKGBUILDs.

Agents must:

- Read and validate metadata without executing commands or sourcing the recipe as a shell script. Arbitrary shell logic and command execution are not allowed in metadata.
- Follow the documented fields, scalar-reference substitutions, source/hash rules, and bare-name or exact-version dependency syntax. Reject unsupported syntax rather than evaluating it as shell.
- Use Bash for optional `prepare()`, `build()`, and `check()` stages and mandatory `package()`, with each stage in a fresh process starting in `$srcdir`. Preserve workspace files, not stage-local shell state.
- Enable `errexit` and `pipefail` for stages, respecting their documented Bash exceptions. A nonzero stage exit must stop execution and prevent acceptance of incomplete staging contents.
- Run defined tests by default; when explicitly disabled, skip `check()` and resolution of `checkdepends`. Reject `checkdepends` without `check()`.
- Make `package()` write to the staging directory supplied by KPB, rather than install into the host system.
- Keep validation, dependency resolution, source acquisition and verification, and build orchestration in the Rust implementation.
- Supply `prefix=/opt/kpb` and keep package output under `$pkgdir/opt/kpb`. Do not incorporate current staging into its own dependency tree or promise relocatable artifacts.
- Use the controlled discovery settings in [docs/build-environment.md](docs/build-environment.md#discovery-environment): KPB tools first, only explicitly selected validated host commands/search paths afterward, and no inherited user PATH, compiler/linker flags, or `LD_LIBRARY_PATH`.
- Treat the specifications as approved requirements, not implemented components. Detailed Bubblewrap policy, provider mappings, runtime validation, artifact format, and future host installation layout remain separate decisions.

Recipes must be treated as untrusted input, and their build functions as **untrusted executable instructions**. Project-maintained recipes are subject to the same precautions.

Agents must consider:

- Source integrity and verification.
- Build-time versus runtime dependencies.
- Reproducibility where practical.
- Build isolation.
- Filesystem permissions.
- Network access during builds.
- Validation before installation.

Never assume that a Git repository or recipe is trustworthy merely because it is publicly accessible.

Avoid executing arbitrary recipe code with elevated privileges.

Bubblewrap is the selected isolation basis. Expose dependencies read-only, deny network access to recipe functions, restrict writes to workspace/staging/private temporary directories, and exclude user home contents, credentials, and session sockets. Do not expose host directories or libraries as implicit dependencies. Check effective isolation support; if the required boundary is unavailable, stop with a diagnostic instead of running without protection. Detailed mounts and per-stage permissions remain to be specified.

Use the host-tool experiment documented in [docs/host-dependencies.md](docs/host-dependencies.md) as bounded evidence for host dependency discovery and Bubblewrap execution. It is not a general provider implementation, Rust recipe executor, or final sandbox policy. Report namespace restrictions without weakening the payload's isolation or claiming a passing test.

## 7. Installation and Removal Safety

Package operations must be designed to minimize the risk of system damage.

Agents should prioritize:

- Building and staging packages before installation.
- Detecting file ownership conflicts.
- Tracking files installed by KPB.
- Preserving files owned by the host package manager.
- Validating dependency relationships before removal.
- Recovering safely from interrupted or failed operations.
- Avoiding partial or inconsistent database updates.

Do not describe operations as atomic or transactional unless the implementation actually provides those guarantees.

Destructive operations require explicit authorization and must never be silently introduced into tests or setup scripts.

## 8. Code Quality

- Follow the existing language conventions and project style.
- Keep modules cohesive and functions reasonably small.
- Prefer explicit error handling.
- Provide actionable diagnostic messages.
- Avoid hidden global state where possible.
- Document public interfaces and non-obvious behavior.
- Add tests for new functionality and bug fixes.
- Avoid unrelated refactoring.

Do not add features solely because they are common in other package managers.

Every significant feature should address an identified KPB requirement.

## 9. Testing

Prefer isolated, reproducible, non-destructive tests.

Tests must not modify the host package database or install files into system directories unless explicitly authorized.

Important test scenarios include:

- Missing dependencies.
- Circular dependencies.
- Version conflicts.
- Duplicate package ownership.
- Failed builds.
- Interrupted installations.
- Invalid recipes.
- Parser and executor scenarios specified in [docs/recipes.md](docs/recipes.md#future-implementation-validation), when those components are implemented.
- Dependency composition, discovery, prefix, and isolation scenarios specified in [docs/build-environment.md](docs/build-environment.md#future-implementation-validation), when those components are implemented.
- Unavailable Git repositories.
- Reuse of compatible validated host dependencies without unnecessary recipe builds.
- Missing or incompatible direct/transitive requirements with no buildable recipe: actionable diagnostics and no recipe execution.
- A recipe exists but one of its own dependencies is unavailable: report the complete requiring chain.
- Preservation of user profiles, shell configuration, and host-managed packages; no automatic native package installation.
- Explicit recording of host files, provider/package identity, effective tool versions, and integrity evidence.
- Acceptance of validated host-bound runtimes, including registered Nix host components, without claiming portability.
- Rejection of unapproved runtime dependencies, ambiguous ownership, integrity failures, and incompatible ABI/architecture.
- Recipe fallback when a compatible host dependency is unavailable and its full recipe graph is satisfiable.
- Host-provided dependencies.
- Removal of packages required by other packages.
- Corrupted or inconsistent package metadata.
- PackageKit unavailable or disconnected.
- Unsupported PackageKit backend operations.
- Missing or ambiguous PackageKit results.
- Host package upgrades affecting KPB-managed software.
- Correct behavior when mock host providers return conflicting information.

Use temporary directories, mock adapters, containers, or other isolated environments where appropriate.

These are requirements for the future implementation, not claims that the resolver, adapters, or recipe executor already exist. The host-GCC experiment covers only the bounded scenarios documented with it.

## 10. Agent Workflow

Before implementing a task:

1. Inspect the relevant source files and documentation.
2. Identify the intended behavior and existing constraints.
3. Determine whether the task requires an architectural decision.
4. Prefer the smallest implementation that satisfies the requirement.

After implementing:

1. Run relevant tests and checks.
2. Review the diff for unrelated changes.
3. Document any new behavior or configuration.
4. Report what changed and why.
5. Clearly identify untested behavior, limitations, and remaining risks.

Never claim that tests passed unless they were actually executed.

## 11. Documentation

Keep documentation consistent with the implementation.

- Update `CONTEXT.md` when an architectural decision is approved.
- Document new recipe formats and interfaces.
- Clearly distinguish implemented features from planned features.
- Do not silently convert proposals into established project requirements.
- Preserve terminology across code and documentation.
- Record significant architectural decisions and their rationale.

## 12. Human Review

AI agents are contributors, not project maintainers.

The human maintainer retains final authority over:

- Architecture.
- Dependencies and technology choices.
- Recipe format.
- Security policies.
- Installation layout.
- Host distribution integration.
- Exceptions to the PackageKit-first approach.
- Breaking changes.
- Release decisions.

When uncertain, explain available alternatives and their trade-offs instead of making irreversible assumptions.

## 13. Guiding Principle

**KPB should remain a focused, understandable, and safe source-based package manager.**

Its goal is to make recipe-driven package management practical across Linux environments while reusing existing host infrastructure whenever appropriate.

**Prefer integration over duplication, explicit ownership over assumptions, and correctness over convenience.**
