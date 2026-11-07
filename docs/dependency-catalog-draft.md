# Dependency catalog schema draft

## Review status

The maintainer authorized drawing GCC and OpenSSL examples before closing the schema. This document proposes field names and semantics for that review. The [catalog structure and declarative-only policy](dependency-catalog.md), registry-owned auxiliary tool requirements, [host selector rules](dependency-catalog.md#host-mapping-selectors), and [Nix discovery representation](dependency-catalog.md#nix-installed-component-discovery) are approved; the remaining field layout is not an implemented or finalized schema.

The examples live under `docs/examples/dependency-catalog/`, outside the future active catalog:

- [gcc.toml](examples/dependency-catalog/gcc.toml): an executable tool with a proposed identity/version/target probe.
- [openssl.toml](examples/dependency-catalog/openssl.toml): a library with development and runtime requirements, including split native packages.

Both are valid TOML. Neither is an operational catalog entry or evidence that a host provider, probe, or package has been tested. No catalog loader or probe registry exists, and the proposed probe IDs must not be treated as implemented.

## Proposed fields

| Field | Proposed meaning |
|---|---|
| `schema_version` | Proposed format version, initially `1`; not an installed package version. |
| `name` | Stable KPB logical dependency name, matching the filename. |
| `kind` | `tool` or `library`. |
| `requirements.executables` | Tool entry-point names to discover and validate, not commands to execute directly from PATH. |
| `requirements.headers` | Required public header names relative to an approved include search root. |
| `requirements.link_libraries` | Library names for link-time discovery; the provider must identify the actual owned files. |
| `requirements.runtime_sonames` | Expected shared-library identities for this draft ABI mapping; not absolute paths discovered on a machine. |
| `validation.probe` | Identifier of a probe that KPB would implement, with no inline script or executable source. |
| `validation.parameters` | Probe-specific typed declarative inputs, accepted only by that probe's defined parameter schema; auxiliary tools are declared by the registry, not these parameters. |
| `mappings` | Explicit provider/distribution-specific routes to candidate installed packages. |
| `mappings.provider` | Provider identifier; examples use `packagekit`, `pacman`, and `nix`. |
| `mappings.distribution` | Exact `/etc/os-release` `ID`; no automatic `ID_LIKE` fallback or inference from the PackageKit backend. |
| `mappings.release` | Optional exact `/etc/os-release` `VERSION_ID` selector. Debian 13 uses `"13"`, not its `trixie` codename; omission means a generic distribution mapping. |
| `mappings.architectures` | Applicable native KPB architecture names; providers translate native package architecture names such as Debian `amd64` to `x86_64`. |
| `mappings.packages` | Candidate native package names for a PackageKit/Pacman mapping. In this draft, all listed names are needed together, not alternatives; Nix uses `discovery` instead. |
| `mappings.discovery` | For Nix, approved value `installed-components`: discover candidates within explicitly selected installed profiles/system roots and their registered references, using the entry's component requirements. No nixpkgs attributes or observed store paths. |

Recipe constraints still come from the approved dependency syntax. The examples do not pin an observed GCC/OpenSSL version or native package revision, and introduce no version-range syntax. An OpenSSL SONAME expectation describes an ABI requirement, not an observed installed version. The OpenSSL example deliberately covers ABI 3; it must not silently accept ABI 4 under unchanged selectors.

## How the two examples would be interpreted

### GCC

Start with a mapping matching the selected provider, exact host distribution `ID`, optional `VERSION_ID`, and internal architecture. Within that provider, prefer a matching release-specific mapping over a generic one and diagnose equally specific ambiguity. Find installed candidates and identify the owner of the discovered `gcc` entry point, its symlinks/wrappers, and actual compiler. The proposed `gcc-tool-v1` probe would verify effective GCC identity/version and native target by executing it in Bubblewrap. Actual command lines belong to KPB's probe implementation, not the TOML file.

The listed `gcc` package is a candidate entry point, not the complete compiler filesystem closure. The provider/inspector still has to identify required interpreters, compiler subprocesses, assembler/linker, plugins/specs, headers, libraries, and data for the intended operation. Native package version and effective compiler version remain separate facts.

### OpenSSL

Resolve the public headers, link-time `ssl`/`crypto` files, and corresponding ABI 3 shared libraries. The proposed `openssl-shared-c-v1` probe would compile, link, and execute a KPB-owned small C program using both libraries in Bubblewrap and record effective version/runtime evidence. Running the `openssl` CLI alone does not establish that library development inputs are usable.

The [approved registry responsibility](dependency-catalog.md#auxiliary-tools-belong-to-the-probe-registry) places the C compiler requirement in the probe definition, not this catalog entry. The resolver must resolve and validate the tool before probing OpenSSL, rather than inherit `CC` or an arbitrary host PATH. It is a validation dependency and does not automatically become an application runtime dependency. Concrete compiler selection and the registry representation remain undecided; this example does not mandate GCC or another compiler.

On Arch, the example uses `openssl` as the candidate package for development and runtime files. On Debian trixie, it requires `libssl-dev` and `libssl3t64` together. Package presence still does not prove compatible files, successful integrity checks, or a passing probe. Additional transitive resources/configuration/plugins must be identified when the selected probe or package actually needs them; these examples are not complete inventories of arbitrary application requirements.

## Scope and unresolved choices

The mapping array illustrates multiple possible routes. Its order does not establish precedence: the approved release-specificity and ambiguity rules apply within each provider. The separate [provider/candidate policy](host-dependencies.md#provider-and-candidate-selection) prefers capable PackageKit and uses approved native providers when needed. Consistent evidence for the same component/files is unified with its origins retained; distinct equally valid candidates require an explicit user choice, and contradictions require diagnostics. Choices never waive validation. The selection UI/CLI and evidence-equivalence implementation remain pending. A PackageKit mapping does not claim its backend is present or supports the required queries.

Nix mappings now use the approved `discovery = "installed-components"` instead of package-name lists. Discovery follows explicitly selected installed profile/system roots and registered references; no full-store scan, nixpkgs evaluation, download, or installation is allowed. Shared requirements identify the desired components; actual paths, hashes, and origins remain local. Selecting discovery roots and implementing compatible development/runtime grouping remain pending. The existing NixOS GCC experiment is not an implementation of this catalog mode.

Before adopting the remaining schema, close probe IDs and typed parameters, registry representation and concrete auxiliary tool requirements, provider-specific discovery details/root selection, and whether ABI selectors belong in shared requirements or individual mappings. Exact host selectors, release-specific precedence, equal-specificity ambiguity, and the Nix discovery representation are approved; their parser/selection implementation is still pending. A future loader should diagnose unsupported schema versions, unknown fields/probe IDs, invalid parameter types, inconsistent kinds/requirements, and ambiguous mappings instead of executing data as code. No loader behavior is implemented by these examples.

## Source checks and validation performed

Package names and development/runtime splits were checked against official distribution pages on 2026-11-07. The [Arch GCC package/file list](https://archlinux.org/packages/core/x86_64/gcc/files/) includes the compiler entry point, and [Debian trixie's GCC description](https://packages.debian.org/trixie/gcc) identifies it as the default compiler dependency package. The [Arch OpenSSL file list](https://archlinux.org/packages/core/x86_64/openssl/files/) contains public headers, link-time files, and shared libraries. Debian's [libssl-dev description](https://packages.debian.org/trixie/libssl-dev) declares its runtime package dependency; its [development file list](https://packages.debian.org/trixie/amd64/libssl-dev/filelist) and [libssl3t64 runtime file list](https://packages.debian.org/trixie/amd64/libssl3t64/filelist) show the split.

These checks establish why the examples use different package groupings, not runtime/provider compatibility on those systems. TOML syntax and consistency of the illustrative fields are checked locally; no PackageKit/Pacman queries, GCC/OpenSSL probes, catalog parser tests, or dependency resolution are claimed for these examples.
