# Dependency catalog

## Approved structure and scope

The initial catalog consists of TOML files versioned alongside KPB's source code and maintained by the project through normal review. Use one file per stable logical dependency under `catalog/dependencies/`, for example `catalog/dependencies/openssl.toml`.

This is an approved documentation-level decision. No catalog entries, detailed TOML schema, loader, or validation registry are implemented yet. The path above describes the intended layout, not an existing catalog implementation. Recipe dependency syntax remains unchanged.

## Shared entry contents

Each entry identifies a logical dependency as a tool or library and describes explicit mappings for the applicable host providers. Mappings identify candidate native packages, required executables or files, and the applicable validation probe by identifier. A library mapping may require multiple native packages for headers, link-time files, and runtime components.

Required artifact names or general discovery criteria belong in the shared catalog. Canonical paths actually resolved on a machine, observed installed versions, local component hashes, and probe results belong in local discovery/validation records. Do not commit a particular machine's observations as general catalog rules. A version constraint or expected identity in a shared validation rule is distinct from an observed installed version.

The catalog expresses candidate mappings, not proof that packages are present or usable. Providers must collect the evidence and perform the [approved validation](host-dependencies.md#minimum-host-dependency-evidence), and the resolver must apply the declared recipe requirements. Missing mappings or insufficient evidence follow the existing recipe/artifact fallback and missing-dependency policy.

## Host mapping selectors

The maintainer approved these matching rules for the initial catalog:

- Match `distribution` exactly against the host's `/etc/os-release` `ID`. Do not infer it from the PackageKit backend or automatically fall back through `ID_LIKE`. Derivatives need explicitly applicable mappings.
- If a mapping declares `release`, match it exactly as text against `VERSION_ID`, not `VERSION_CODENAME`. A mapping without `release` is generic for that distribution. For example, the Debian 13 mappings use `release = "13"`; `"13"` is not an installed package version.
- Match architecture using KPB's internal native architecture names. The provider translates native package names such as Debian `amd64` into KPB `x86_64`; do not compare the native string directly with the catalog selector.
- Among applicable mappings for the same provider, distribution, and architecture, a matching release-specific mapping takes precedence over a generic mapping. If multiple mappings at the highest applicable specificity remain, report ambiguity; do not pick by file order or merge their package lists.

| Applicable mappings within one provider/distribution/architecture | Selection |
|---|---|
| One generic mapping | Generic mapping. |
| One generic and one matching release-specific mapping | Release-specific mapping. |
| Generic mapping and a release-specific mapping for another release | Generic mapping. |
| Two equally specific matching mappings | Ambiguity diagnostic. |
| No matching mapping | Host requirement remains unresolved under the existing artifact/recipe fallback policy. |

Missing host evidence cannot establish an exact selector match: in particular, do not substitute a codename when `VERSION_ID` is unavailable. These rules select mappings within a provider. Apply the separate [provider/candidate policy](host-dependencies.md#provider-and-candidate-selection): prefer capable PackageKit, use approved native providers when needed, unify consistent evidence for the same component/files, and stop for explicit choice between distinct equally valid components. Selecting a mapping still requires normal ownership, integrity, compatibility, and probe evidence before its dependency can be accepted; a user choice cannot waive those checks.

The selector policy is approved but not implemented. The remaining TOML schema, host identity parsing, and native architecture translation implementation remain pending.

## Nix installed-component discovery

The maintainer approved `discovery = "installed-components"` for Nix mappings in place of `packages`. For example:

```toml
[[mappings]]
provider = "nix"
distribution = "nixos"
architectures = ["x86_64"]
discovery = "installed-components"
```

The entry's shared requirements still describe the executables, headers, link-time libraries, and runtime components to find. The provider searches candidates in explicitly selected installed profiles and system roots and follows their registered store references. It must establish each candidate's ownership, integrity, compatibility, and functional probe evidence before selection. Development and runtime files may belong to different compatible store outputs; their grouping and provenance must be validated rather than inferred from similar names.

Do not put nixpkgs attributes, profile names used as package identities, or machine-specific store paths in the shared mapping. A directory basename is not proof of package identity/version. Concrete paths, hashes, discovered profile/root origins, and validation results belong in local records. Metadata already present on the host can support evidence, but must not be evaluated as an instruction to fetch or rebuild anything.

Discovery is read-only and limited to selected installed roots and their registered references. Do not scan the entire store indiscriminately, evaluate nixpkgs, download missing outputs, install packages, or change profiles. Missing required components follow the existing artifact/recipe fallback or report-and-stop policy. Discovering references does not authorize mounting the entire reference graph without selecting and recording the required inputs.

The example selects NixOS through the normal exact distribution/architecture rules; using Nix on another distribution requires an explicitly applicable mapping. Provider/candidate precedence, integrity requirements, and Bubblewrap remain unchanged.

This representation is approved, not implemented. The exact set/configuration of discovery roots, profile formats and capability handling, candidate grouping, and general discovery algorithm remain pending. The existing NixOS GCC experiment handles one tool and does not implement this catalog mode or generic library discovery.

## Declarative validation references

Catalog entries are data. They reference validation probes implemented by KPB using identifiers; they do not contain arbitrary commands, shell functions, or executable validation scripts. The concrete probe implementations still run under the required Bubblewrap boundary. Recipe build functions remain a separate executable format.

### Auxiliary tools belong to the probe registry

The maintainer approved keeping auxiliary tool requirements in KPB's implemented probe registry. Each probe definition declares the tools it needs; catalog entries only select a probe identifier and supply its accepted declarative parameters. Do not repeat or override the probe's internal tool requirements in individual catalog entries.

For example, an OpenSSL compile/link/run probe needs a C compiler. The registry declares that requirement, and the resolver identifies and validates a suitable host tool or resolves an available validated artifact/buildable project recipe before running the dependent probe. Never take an undeclared compiler from inherited `CC` or PATH. If the requirement cannot be satisfied, report it and stop without executing that probe or the dependent recipe build.

Record these tools as validation dependencies. They do not automatically become runtime dependencies of the application or entries in its recipe's `checkdepends`; dependency roles and actual runtime requirements remain explicit. An unavailable required tool does not authorize skipping a mandatory validation probe or weakening Bubblewrap.

This responsibility split is approved. Registry representation, concrete probe definitions, compiler selection, typed parameters, and integration of validation prerequisites into dependency planning remain unimplemented and require further design. No probe registry or tool-selection API is introduced by this document.

### Remaining schema work

The TOML schema, identifier vocabulary, probe definitions/parameters, provider-specific entry fields, and loader diagnostics require further decisions. Do not present an illustrative field layout as an implemented or approved schema.

A [schema draft with GCC and OpenSSL examples](dependency-catalog-draft.md) is available for review. The examples are stored under `docs/examples/dependency-catalog/`, not the future active catalog, and do not close these pending decisions.

## Maintenance and local state

The project maintains the initial catalog together with KPB. Mapping changes are explicit, versioned, and reviewed. Initially there are no external catalogs or automatic mapping updates.

Keep machine-specific discovery records and experiment results outside versioned catalog data. For development, the ignored `.local/` directory is available for local outputs; this does not select a production state-directory layout or installed-package database.

Future implementation checks should verify one entry per logical dependency, tool/library classification, explicit provider mappings, references to implemented probe identifiers, declarative-only contents, and separation of shared rules from local observations. No parser or executor tests are claimed by this specification.
