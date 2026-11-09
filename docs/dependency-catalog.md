# Dependency catalog schema

This is the approved initial data contract, not an implemented loader. Architecture, host discovery and probe behavior are owned by [decisions.md](decisions.md). Examples under [examples/dependency-catalog/](examples/dependency-catalog/) are documentation fixtures, not active catalog entries.

## Layout and validation

Use project-maintained TOML at `catalog/dependencies/<name>.toml`, one logical dependency per file, versioned with KPB. Keep observed machine paths, versions, hashes and probe results in local run evidence. No external catalogs, automatic mapping updates, scripts or inline probe code.

Reject unknown fields/probes, unsupported versions, wrong types, missing required values, duplicate list elements, crossed tool/library fields and ambiguous mappings. Diagnostics identify file, field/mapping and reason. Preserve declaration order/case; do not trim, normalize, deduplicate, expand environment variables, repair data or evaluate shell. An invalid entry stops resolution before builds; it is not missing-package fallback.

## Fields and defaults

| Field | Type and rule |
|---|---|
| `schema_version` | Required integer `1`. |
| `name` | Required logical name matching filename stem and `[a-z0-9][a-z0-9._+-]*`. |
| `kind` | Required `tool` or `library`. |
| `requirements` | Required table; only fields for its kind. |
| `requirements.executables` | Required nonempty text list for tools; forbidden for libraries. |
| `requirements.link_libraries` | Required text list for libraries; forbidden for tools. Empty only with nonempty `headers` for a header-only requirement. |
| `requirements.headers` | Library text list, default `[]`; forbidden for tools, even if empty. |
| `validation` | Required table. |
| `validation.probe` | Required known probe ID of the appropriate kind. |
| `validation.parameters` | Table, default `{}`; only the selected registry schema's keys/types/values/defaults. Cannot override auxiliary requirements. |
| `mappings` | Required nonempty array of mapping tables. |
| `mappings.provider` | Required `packagekit`, `pacman` or `nix`. |
| `mappings.distribution` | Required exact host distribution ID. |
| `mappings.release` | Optional exact release; omission means generic, empty text is invalid. |
| `mappings.architectures` | Required nonempty list of registered KPB architecture names; initial registry is `x86_64`. |
| `mappings.packages` | Required nonempty native-name list for PackageKit/Pacman. All members are required together, not alternatives. Forbidden for Nix. |
| `mappings.discovery` | Required `"installed-components"` for Nix; forbidden for other providers. No inferred package names, nixpkgs attributes or observed store paths. |
| `mappings.runtime_sonames` | Required nonempty text list for mappings whose library probe requires shared runtime identities. Forbidden for tools. Non-shared requirements may omit it; omission never infers linkage. |

Required fields have no defaults except where explicitly stated. Collections are text lists with exact duplicates rejected. Entirely empty library requirements are invalid. Header-only representation is allowed, but its functional probe family remains deferred under D07; a representable entry is not operational without a compatible registered probe.

Public headers, link-library names and the probe are logical requirements. Expected native SONAMEs belong in each mapping, never `requirements.runtime_sonames`. SONAME matches do not replace version constraints or functional ABI checks.

## Identifier rules

| Value | Grammar |
|---|---|
| Executable, link-library name, SONAME | ASCII `[A-Za-z0-9_][A-Za-z0-9._+-]*`. No paths, spaces, options, globs or shell operators. |
| Header | Relative `/`-separated segments using the grammar above. No empty segments, `.`/`..`, absolute paths or backslashes. |
| Probe ID | `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`, plus a mandatory registry lookup. |
| Distribution/release/architecture | Nonempty literal text without whitespace/control characters; architecture also requires registry membership. |
| Native package name | Nonempty literal without whitespace/control characters, validated using its provider/backend naming rules, not the logical-name regex. |

Reject whole identifiers equal to `.` or `..`. Quoting cannot legalize an invalid value. These are discovery data, not command strings or proof of file ownership; pass arguments as data, never interpolated shell code.

## Mapping selectors

- Match `distribution` to exact `/etc/os-release` `ID`; no `ID_LIKE` fallback or inferred backend identity.
- Match declared `release` to exact textual `VERSION_ID`, not a codename. Missing evidence cannot establish an exact match.
- Providers translate native package architecture names into KPB names; do not compare native strings directly to catalog selectors.
- Within one provider/distribution/architecture, a matching release-specific mapping outranks a generic one. Equally specific matches are ambiguous; never choose by order or merge package lists.
- No applicable mapping leaves the host requirement unresolved. A mapping does not prove provider availability, candidate validity or package presence.

Provider/candidate selection and Nix root discovery are defined only in [the project decisions](decisions.md#host-providers-and-evidence). Catalog order does not override them.

## Examples

[gcc.toml](examples/dependency-catalog/gcc.toml) selects the GCC tool probe. [openssl.toml](examples/dependency-catalog/openssl.toml) separates logical SSL/crypto requirements from mapping-specific ABI identities and native development/runtime package groups. Their probe contracts are approved, not implemented. The examples do not guarantee those distribution backends are supported or the components installed.
