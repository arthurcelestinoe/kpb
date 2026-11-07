# Kobalt Package Builder (KPB)

## Project Context and Vision

### 1. Overview

**Kobalt Package Builder (KPB)** is an experimental, source-based package manager for Linux.

KPB aims to provide a flexible system for building, installing, updating, and removing software using build recipes obtained from Git repositories.

The project draws inspiration from:

- **Arch User Repository (AUR):** approachable, recipe-driven software building.
- **nixpkgs:** Git-based distribution and version control of package definitions.
- **Traditional Linux package managers:** dependency resolution, package ownership tracking, and installed-package databases.
- **PackageKit:** distribution-independent access to native package management capabilities.

KPB does not aim to reproduce any of these systems exactly.

Its goal is to combine selected ideas into a coherent, independent package management architecture.

### 2. Motivation

Linux distributions already provide mature package management systems.

However, source-based software installation often requires distribution-specific packaging infrastructure, manual compilation, or reliance on third-party build tools.

KPB explores a different approach:

**What if a source-based package manager could use simple build recipes, obtain them directly from Git repositories, and reuse dependencies already installed by the host distribution through a common integration interface?**

This would allow KPB to operate as an additional package management layer without requiring users to replace their existing distribution.

### 3. Core Goals

KPB is intended to support:

1. Building software from source using structured recipes.
2. Installing, upgrading, and removing KPB-managed packages.
3. Resolving package dependencies.
4. Maintaining an installed-package database.
5. Obtaining and updating recipes from Git repositories.
6. Reusing compatible dependencies provided by the host distribution.
7. Tracking package ownership and dependencies.
8. Using PackageKit as the preferred host package discovery interface.
9. Operating independently of a specific desktop environment or init system.

The initial focus is on Linux distributions that already have a functioning native package manager.

### 4. What KPB Is Not

KPB is not intended to be:

- A complete replacement for every Linux package manager.
- A clone of Gentoo Portage.
- A clone of Nix or its functional package management model.
- A replacement for the AUR.
- A system that necessarily rebuilds all dependencies from source.
- A tool tied to KDE, Qt, systemd, or a specific Linux distribution.
- A replacement for PackageKit or native package management backends.

The letter **K** in Kobalt is a naming choice, not a requirement for KDE integration.

### 5. Package Recipes

Recipes describe how software is obtained, built, and prepared for installation.

A future recipe format may include:

- Package name and version.
- Description and license.
- Source URLs or Git references.
- Source integrity information.
- Build dependencies.
- Runtime dependencies.
- Version constraints.
- Build configuration.
- Build instructions.
- Installation and staging instructions.
- Optional features or build variants.

The exact recipe syntax and execution model are **not yet finalized**.

The project should favor readability, maintainability, and predictable behavior.

### 6. Git-Based Recipe Repositories

KPB should support Git repositories as sources of package recipes.

This allows package definitions to be:

- Version controlled.
- Reviewed through standard Git workflows.
- Maintained by different communities.
- Updated independently of the KPB executable.
- Distributed without requiring a centralized package registry.

Potential future capabilities include repository priorities, pinned revisions, and trusted repository policies.

The initial repository layout and synchronization behavior remain to be defined.

### 7. Dependency Management

KPB is responsible for resolving dependencies required for building and running software.

A key design principle is **host dependency reuse**.

For example, if a package requires a compatible version of OpenSSL and the host distribution already provides it, KPB should be able to recognize and reuse that installation.

KPB should distinguish between:

- Dependencies managed by KPB.
- Dependencies provided by the host distribution.
- Build-time dependencies.
- Runtime dependencies.

KPB must not assume ownership of externally managed dependencies.

The PackageKit integration will provide information that helps the KPB resolver determine whether host-installed packages can satisfy recipe requirements.

However, PackageKit is not responsible for resolving the complete dependency graph of KPB recipes.

Dependency naming, provider mapping, version compatibility, and ABI compatibility require further design.

Automatic installation of missing dependencies through the host package manager is not an established requirement.

### 8. Host Integration Architecture

#### 8.1 PackageKit-first design

KPB adopts **PackageKit as its preferred integration layer for host package discovery and inspection**.

PackageKit provides a D-Bus API that abstracts capabilities of several native Linux package managers through distribution-specific backends.

Instead of implementing direct integrations with every supported distribution, KPB should initially use PackageKit to query host package information.

Relevant capabilities include:

- Discovering installed packages.
- Resolving package identifiers.
- Inspecting package metadata and versions.
- Querying dependencies and reverse dependencies.
- Discovering provided capabilities.
- Retrieving installed-file information when available.

These operations are backend-dependent and cannot be assumed to work universally.

The first implementation should prioritize read-only access.

Package installation and removal performed by KPB itself will remain under KPB's own package management subsystem.

#### 8.2 Provider abstraction

KPB should expose a distribution-independent internal interface for host package information.

A conceptual name for this interface is `HostDependencyProvider`.

The architecture can be represented as:

```text
                 Kobalt Package Builder
                           |
                  Dependency Resolver
                           |
                 HostDependencyProvider
                           |
                    PackageKit Adapter
                           |
                       D-Bus API
                           |
                       PackageKit
                           |
             +-------------+-------------+
             |             |             |
            ALPM          APT           DNF
             |             |             |
           Pacman        dpkg          RPM
```

This is a conceptual diagram, not a finalized implementation design.

The provider abstraction should allow alternatives to PackageKit without requiring changes to the dependency resolver.

#### 8.3 Native adapter exceptions

Direct native package manager adapters may be implemented when PackageKit cannot satisfy a requirement.

Possible reasons include:

- PackageKit is not installed or cannot run.
- A backend does not implement a required operation.
- PackageKit cannot expose sufficient metadata.
- A platform requires specialized behavior.
- A documented compatibility limitation prevents reliable operation.

Such adapters should implement the same internal provider interface.

They should not duplicate unrelated package management functionality.

#### 8.4 Initial distribution considerations

Potential integration targets include:

- **Arch Linux and Artix Linux:** through PackageKit's ALPM backend, subject to real-world testing.
- **Debian and derivatives:** through the APT backend.
- **Fedora and derivatives:** through the relevant DNF backend.
- **openSUSE:** through the Zypper backend.

These are potential targets, not guarantees of support.

The availability and functionality of PackageKit depend on each distribution and installed backend.

NixOS may require separate consideration because its package and system management model differs substantially from conventional mutable distributions.

#### 8.5 Runtime capability detection

KPB should not assume that every PackageKit backend exposes identical features.

The integration layer should:

1. Detect PackageKit availability.
2. Identify supported operations.
3. Query packages through supported interfaces.
4. Normalize metadata into KPB's internal representation.
5. Report unsupported capabilities explicitly.
6. Use an approved alternative provider when available.

Missing capabilities must not silently produce incorrect dependency resolution.

### 9. Package Database

KPB will maintain its own database of managed packages.

The database should eventually record information such as:

- Package name and installed version.
- Recipe and repository origin.
- Installation status.
- Installed file ownership.
- Direct and transitive dependencies.
- Dependency provider information.
- Build and installation metadata.

Dependencies supplied by the host must be distinguishable from dependencies installed by KPB.

For example:

```text
Package: example
Version: 1.2.0
Managed by: Kobalt

Dependencies:
  cmake       -> Host (build)
  openssl     -> Host (runtime)
  qt6-base    -> Host (runtime)
  libexample  -> Kobalt (runtime)
```

Host-managed packages remain under the ownership of their native package manager.

KPB must never remove host-owned dependencies merely because a KPB-managed package no longer needs them.

The database must remain logically separate from the host package manager's database.

A storage implementation, such as SQLite, may be evaluated, but no database engine has been selected yet.

### 10. Build and Installation Model

A proposed model separates package construction from system installation.

Possible stages:

1. Retrieve and validate the recipe.
2. Resolve dependencies, including host-provided dependencies.
3. Obtain and verify source code.
4. Prepare the build environment.
5. Compile the software.
6. Stage the installation files.
7. Inspect the resulting package.
8. Check for conflicts with KPB-managed and host-managed files.
9. Install the package and update the KPB database.

This workflow is a **design proposal**, not a statement of implemented functionality.

The package artifact format, installation prefix, filesystem layout, and rollback strategy remain open questions.

### 11. Coexistence With Native Package Managers

KPB is intended to operate alongside existing package managers.

The host package manager retains ownership of its installed packages and system-managed files.

KPB will manage only the packages it installs.

A critical challenge is avoiding filesystem ownership conflicts.

Potential strategies include:

- A dedicated installation prefix for KPB-managed software.
- Configurable installation prefixes.
- File ownership checks before installation.
- Explicit conflict detection against the host package database.

The final installation layout has not been selected.

KPB should not assume that PackageKit alone provides sufficient information to prevent every filesystem conflict.

### 12. Host Package Updates and Compatibility

Reusing host dependencies creates a potential compatibility issue.

A KPB-managed application may be compiled against a library provided by the host distribution.

If the host later updates that library, the application may require rebuilding.

KPB should consider recording:

- The dependency provider.
- The resolved package version.
- Relevant compatibility information.
- The KPB packages depending on that external component.

Potential future features include:

- Detecting potentially incompatible host updates.
- Warning users about affected packages.
- Rebuilding selected KPB-managed software.
- Validating runtime dependencies after host updates.

These capabilities are exploratory and not part of a confirmed initial milestone.

### 13. Security Considerations

Source-based package management introduces significant security concerns.

Recipes may execute arbitrary build commands, while package installation can modify sensitive filesystem locations.

KPB should eventually provide safeguards for:

- Untrusted recipes.
- Source verification.
- Build isolation.
- Privilege separation.
- Filesystem conflicts.
- Dependency integrity.
- Failed or interrupted operations.
- Untrusted Git repositories.
- Incorrect or incomplete host package information.

Security is an architectural requirement, not a feature to be postponed until the project becomes mature.

The exact sandboxing and transaction mechanisms remain undecided.

### 14. Future Possibilities

Long-term possibilities include:

- Additional host distribution adapters.
- Package caching.
- Binary artifacts generated from source builds.
- Reproducible builds.
- Advanced dependency providers.
- Package rebuild detection after host library updates.
- Community-maintained recipe repositories.
- A Linux distribution using KPB as its primary package manager.

These are exploratory directions rather than committed milestones.

In particular, a dedicated KPB-based distribution is a **possible future experiment**, not the immediate objective.

### 15. Current Development Status

KPB is in an early experimental stage.

The initial concept and prototype work began during experimentation with an AI coding model.

The project is expected to continue through AI-assisted development under human review.

The following architectural direction has been established:

**KPB should prefer PackageKit for host package discovery while retaining an internal provider abstraction that permits native integrations when necessary.**

However, this integration has not yet been validated as part of a completed KPB implementation.

No programming language, recipe syntax, database engine, installation layout, or definitive implementation architecture is established by this document.

Existing source code, when available, should be examined before making implementation decisions.

### 16. Open Architectural Questions

The following questions require explicit decisions:

1. Which programming language and runtime should KPB use?
2. What should the recipe format look like?
3. Should recipes be executable scripts, structured data, or a hybrid?
4. How should Git repositories organize recipes?
5. How should dependency providers and versions be represented?
6. How should PackageKit results be normalized?
7. Which PackageKit capabilities are strictly required for initial support?
8. Should PackageKit be an optional or required runtime dependency?
9. Which host distribution should be tested first?
10. Where should KPB-managed packages be installed?
11. Should installation prefixes be configurable?
12. What database technology should be used?
13. How should builds be isolated?
14. What guarantees should installation and removal provide?
15. How should KPB detect host-owned filesystem conflicts?
16. Should KPB generate reusable package artifacts?
17. How should KPB handle dependency changes following host system updates?

Agents should not silently resolve these questions without maintainer approval.

### 17. Development Philosophy

KPB should grow incrementally.

Early development should prioritize a reliable core over broad feature coverage.

Existing distribution infrastructure should be reused whenever it can safely satisfy the project's requirements.

Avoid implementing separate distribution-specific integrations without a demonstrated need.

The project should remain understandable, modular, and adaptable.

**The long-term ambition is flexibility; the short-term priority is correctness.**
