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

These are overall project goals. The initial milestone uses only project-maintained recipes and dependencies supplied by those recipes, with the temporary Nix build and bootstrap exception defined below. PackageKit host integration is deferred to a later milestone.

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

### 3.1 Temporary Nix bootstrap

Nix is approved only as a temporary source of build tools and inputs that project recipes cannot yet provide, including the initial compiler. This approval does not establish Nix as a host discovery provider or a runtime dependency provider for final packages.

Agents must:

- Require Nix and flake support to be already available when needed; never install/configure Nix or enable flakes automatically. Report missing support with an actionable diagnostic.
- Preserve user profiles, shell configuration, and host-managed packages. Downloads and writes to the Nix store and caches are allowed.
- Expose Nix tools only to the build process, without persistent changes to the user's environment.
- Keep recipe definitions independent of Nix. Define temporary tools in version-controlled `flake.nix` and `flake.lock`; normal builds must use the committed lock without generating or updating it. Lock updates require an explicit maintainer operation. The mapping and recording of recipe bootstrap exceptions remain undecided; never infer Nix package names from recipe names.
- Record each temporary Nix dependency and its justification, and replace it once a validated chain of project recipes provides the same function.
- Validate final artifacts for runtime dependencies on Nix, including interpreters, libraries, and store paths. Do not accept a final package if runtime independence from Nix cannot be demonstrated.

Do not assume that using a Nix compiler produces an artifact independent of Nix, or that a Nix development environment provides a security sandbox. Build isolation remains a separate requirement.

Removing Nix is the goal, but do not claim that all external bootstrap inputs can be eliminated. The initial compiler remains an explicit requirement until an alternative is defined.

## 4. Host Distribution Integration

### 4.1 PackageKit-first approach

**PackageKit is the preferred integration layer for querying packages provided by the host distribution.**

This applies to future host integration, outside the initial milestone. The approved temporary Nix bootstrap in section 3.1 does not change this future direction.

Agents should use PackageKit instead of implementing separate integrations for APT, DNF, Pacman, Zypper, and similar package managers whenever its supported capabilities satisfy KPB's requirements.

The first host integration milestone should focus on read-only operations, including:

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

Such exceptions require maintainer approval.

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

In the initial milestone, resolve dependencies through project recipes, with only the explicit temporary build and bootstrap exceptions described in section 3.1. Nix must not replace KPB's dependency resolver or provide runtime dependencies for final packages.

glibc is the approved initial C runtime for a native x86_64 Linux demonstration in C, with GCC and GNU Binutils temporarily supplied by Nix. C++ packages are deferred. Follow [the runtime decision](docs/build-environment.md#initial-c-runtime): use a KPB-built loader under `/opt/kpb/lib` and explicit RUNPATH to `/opt/kpb/lib` in executables and libraries requiring it. Do not add a preliminary musl stage or use Nix/host runtime libraries as implicit substitutes. Versions, prerequisites, the exact loader filename, and detailed toolchain settings remain undecided.

Compose validated direct runtime/build dependencies, enabled test dependencies, and their required transitive runtime dependencies into one read-only tree per build. Do not propagate dependencies used only to build an already completed dependency. Allow one version per package name; reject incompatible requirements and file/link/type collisions without automatic alternative builds or silent overwrites. Shared directories may be merged while retaining contributor ownership. Keep temporary bootstrap tools and current staging separate from this tree.

In future host integration, PackageKit acts as a source of host package information, not as a replacement for KPB's dependency resolver.

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
- Use the discovery settings in [docs/build-environment.md](docs/build-environment.md#discovery-environment): KPB tools first, explicit bootstrap tools only, pkg-config and CMake paths under `/opt/kpb`, and no inherited user PATH or automatic compiler/linker flags or `LD_LIBRARY_PATH`.
- Treat the specifications as approved requirements, not implemented components. Detailed Bubblewrap policy, bootstrap configuration, runtime validation, artifact format, and future host installation layout remain separate decisions.

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
- Missing Nix when an explicit bootstrap input requires it.
- Preservation of user profiles, shell configuration, and host-managed packages during Nix-assisted builds.
- Explicit declaration and recording of temporary Nix bootstrap inputs.
- Rejection of final artifacts with Nix runtime dependencies or unverified runtime independence.
- Replacement of a temporary Nix tool with a validated project recipe.
- Host-provided dependencies.
- Removal of packages required by other packages.
- Corrupted or inconsistent package metadata.
- PackageKit unavailable or disconnected.
- Unsupported PackageKit backend operations.
- Missing or ambiguous PackageKit results.
- Host package upgrades affecting KPB-managed software.
- Correct behavior when mock host providers return conflicting information.

Use temporary directories, mock adapters, containers, or other isolated environments where appropriate.

Host provider and PackageKit scenarios apply when host integration is introduced; they do not require implementing it in the initial milestone. The Nix scenarios above are requirements for future bootstrap implementation, not claims of existing tests.

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
