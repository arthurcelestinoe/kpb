# KPB recipe format

## Status and scope

This document specifies the approved initial recipe format. It describes requirements for a future implementation; no recipe parser, executor, resolver, or source acquisition is implemented yet.

A recipe is named `KPB.recipe` and describes one package. It combines a restricted metadata block with Bash functions, inspired by Arch PKGBUILDs and BSD ports. Existing PKGBUILDs are not assumed to be compatible.

The initial milestone builds project-maintained recipes, reuses explicitly validated host dependencies to minimize compilation, and produces artifacts in staging without system installation. Host-bound runtimes are permitted under the [host dependency policy](host-dependencies.md); recipe names and native package names are not automatically interchangeable. If a required dependency has no compatible validated host component or buildable project recipe/artifact, stop and inform the user before obtaining sources or executing recipe functions.

## File structure and metadata syntax

All metadata assignments precede function definitions. Blank lines, comments beginning with `#` outside quoted text, and parenthesized lists spanning multiple lines are allowed. Each field or auxiliary variable may be assigned only once.

Metadata values are scalar text, a positive integer for `pkgrel`, or lists of text. Literal values may be single-quoted, double-quoted, or simple unquoted tokens without whitespace or shell metacharacters. Use quotes for URLs and dependency constraints. Lists use whitespace-separated items, for example `license=('MIT' 'BSD-2-Clause')`; commas are not separators. An empty list is `()`.

Only double-quoted text supports substitution, using `${variable}`. A reference must name a previously declared scalar metadata field or scalar auxiliary variable. Auxiliary names begin with `_` and otherwise use letters, digits, and underscores. An auxiliary can reference earlier scalars in the same way. Substitution inserts text without reinterpreting it as shell syntax or recursively expanding it. Single-quoted values remain literal.

For example:

```bash
pkgname=example
pkgver=1.2
_source_dir="${pkgname}-${pkgver}"
source=("https://example.org/${_source_dir}.tar.xz")
```

This is a metadata fragment, not a complete recipe. Metadata inspection must never execute commands or source the recipe in Bash. In metadata, reject:

- Command substitutions, backticks, arithmetic, shell operators, conditionals, and loops.
- Environment lookups, `$variable` shorthand, parameter operators such as `${name:-default}`, and references to lists.
- Undefined or forward references, duplicate assignments, list-valued auxiliary variables, and unknown fields other than scalar auxiliaries.
- Unsupported syntax or incorrect field types, rather than silently interpreting them as Bash.

Top-level commands are forbidden even after function definitions. Function bodies contain executable Bash and are distinct from the restricted metadata block.

### Fields

| Field | Type | Requirement and meaning |
|---|---|---|
| `pkgname` | Text | Required; matches `[a-z0-9][a-z0-9._+-]*`. |
| `pkgver` | Text | Required, nonempty upstream version without whitespace, `/`, or `=`. SemVer is not required. |
| `pkgrel` | Integer | Required, positive recipe revision for the same upstream version. |
| `pkgdesc` | Text | Required, nonempty package description. |
| `license` | Text list | Required and nonempty; use SPDX identifiers where applicable. Describes the packaged software's licenses. |
| `arch` | Text list | Required and nonempty; accepted native host architectures, or `('any')` alone for architecture-independent content. |
| `url` | Text | Optional project homepage. |
| `source` | Text list | Required and nonempty; HTTPS URLs or recipe-relative files. |
| `sha256sums` | Text list | Required; one 64-digit hexadecimal SHA-256 checksum per source, in matching order. |
| `depends` | Text list | Runtime dependencies; defaults to empty. |
| `makedepends` | Text list | Additional build dependencies; defaults to empty. |
| `checkdepends` | Text list | Additional test dependencies; defaults to empty. |

Only native builds are covered. Architecture-specific recipes must match the host architecture; `any` is a declaration of architecture-independent content, not permission to cross-compile.

### Dependencies

Each dependency is a package name or a package name followed by `=` and an exact upstream version, for example `libexample` or `libexample=1.2`. Names follow the `pkgname` rule and exact versions follow the `pkgver` rule. Empty names or versions, multiple `=` separators, comparison operators, and version ranges are invalid.

Exact matching compares `pkgver` as text, excluding `pkgrel`: `1.2` and `1.2.0` are different. A bare name imposes no version constraint. There is no version ordering, range syntax, or virtual provider syntax in this version. These declarations do not establish ABI compatibility by themselves.

Dependency names are stable KPB names, such as `gcc`, `make`, or `openssl`, shared across hosts. Each provider maintains an explicit mapping to installed native packages and required files; recipes do not use host-specific package identifiers. A matching native package name/version is not sufficient: tools require effective-version validation, and libraries require the relevant headers, link-time files, runtime components, and compatibility evidence. See [the approved mapping model](host-dependencies.md#approved-dependency-naming-and-mapping).

Without a mapping or sufficient host evidence, resolve through an available validated KPB artifact or buildable project recipe. If neither can satisfy the requirement, report it and stop. The [catalog](dependency-catalog.md) uses project-maintained TOML files under `catalog/dependencies/`, one per logical dependency, with explicit provider mappings and built-in probe identifiers. Local discoveries stay outside shared entries. Its detailed schema, concrete mappings, and loader remain unimplemented; recipes do not embed or execute catalog validation commands.

Host evidence must meet [the approved minimum](host-dependencies.md#minimum-host-dependency-evidence): ownership/files, tool version/architecture or library development/runtime compatibility, offered integrity checks, and a minimal functional probe in Bubblewrap (tool execution or library compile/link/run). Record unsupported integrity checking explicitly; actual integrity mismatches reject the candidate. These checks belong to provider/dependency validation, not executable recipe metadata, and do not replace a recipe's `check()` stage.

`depends` records runtime requirements that must also be available during the build. `makedepends` adds build-only requirements, and `checkdepends` adds requirements only when `check()` will run. Dependency roles must remain distinguishable when the same package serves multiple roles. The resolver reuses compatible validated host components or available validated recipe artifacts, and builds project recipes for unsatisfied requirements. Native provider mapping and validation are separate from recipe syntax.

The [build environment](build-environment.md) composes KPB-managed dependencies read-only at `/opt/kpb` and exposes selected host components through an explicit read-only mount plan. Build-only dependencies used to produce a completed dependency are not automatically propagated to its consumer. Allow one selected version per logical dependency and reject incompatible requirements or conflicting file contributions. Resolve the full selected graph, including transitive and enabled test requirements, before starting recipes. If it is incomplete, report each unresolved requirement, constraint, role, requiring chain, and reason; never automatically install host packages or download replacement tools.

## Sources and integrity

KPB must obtain all declared sources and verify all corresponding hashes before executing any recipe function. Both downloaded and local files require hashes; `SKIP` is not supported. A missing file, download failure, checksum mismatch, or list length mismatch stops the operation.

Local paths are relative to the recipe directory. They must stay inside that directory, including after resolving symbolic links. Absolute local paths and paths that escape the recipe directory are invalid.

Source files are identified by their basenames in the build workspace. Reject conflicting destination names rather than overwriting a source. For HTTPS sources, use the URL path's final filename; source renaming syntax is not supported.

After verification, KPB automatically extracts `.tar`, `.tar.gz`, and `.tar.xz` archives into `$srcdir`. Other files, including patches, are made available in `$srcdir` without extraction or automatic patch application. Recipes apply patches explicitly in `prepare()` when needed. Unsupported archive formats are treated as ordinary files in this version.

Extraction must reject paths or link targets escaping `$srcdir`, and must not overwrite entries belonging to other sources. Filename conflicts and unsafe archives are errors, not an instruction to try another extraction method.

Git source checkouts, source renaming, per-source extraction controls, and checksum bypasses are outside this version. Git-based recipe repositories remain a separate concept from obtaining a package's source code from Git.

## Build variables and functions

Each stage receives validated metadata and scalar auxiliaries as Bash variables, list metadata as Bash arrays, and all declared recipe functions. KPB also supplies these absolute paths:

| Variable | Meaning |
|---|---|
| `recipedir` | Directory containing the recipe and its auxiliary files. |
| `srcdir` | Verified files and extracted sources; initial working directory for every stage. |
| `builddir` | Separate workspace for out-of-tree builds. |
| `pkgdir` | Staging root, empty at the start of the build sequence. |
| `prefix` | Fixed at `/opt/kpb` in the initial milestone. |

`prefix` describes the intended destination inside the sandbox, not a directory into which a recipe may directly install. For a build system honoring `DESTDIR`, `make DESTDIR="$pkgdir" install` stages files under `$pkgdir/opt/kpb`. Current staging remains separate from the read-only dependency tree during the build. KPB will not create or populate the host's `/opt/kpb` in this milestone. Artifacts are bound to this prefix without a relocation guarantee; prefix configurability and future host installation layout are deferred.

The [build environment contract](build-environment.md#discovery-environment) also defines PATH, pkg-config, and CMake discovery. It does not inherit the user's PATH, add automatic compiler/linker flags, or supply `LD_LIBRARY_PATH`. Required recipe-specific adjustments must be explicit.

The sequence is:

1. Validate the recipe and resolve dependencies.
2. Obtain and verify sources, then extract supported archives.
3. Run `prepare()` if present.
4. Run `build()` if present.
5. Run `check()` if present and enabled.
6. Run the required `package()` function.
7. Validate the staged artifact and its declared runtime requirements, including approved host runtimes and host compatibility, before accepting it.

| Function | Required | Responsibility |
|---|---|---|
| `prepare()` | No | Prepare extracted sources, such as applying declared patches. |
| `build()` | No | Compile or otherwise generate package contents. May use `$builddir`. |
| `check()` | No | Test the build before packaging. |
| `package()` | Yes | Populate `$pkgdir`, without installing into the host system. |

Functions use `name() { ... }` definitions with no declared parameters. Auxiliary Bash functions whose names begin with `_` are permitted. Other stage names are not part of this version. A recipe without compilation can omit `build()`.

Every stage runs in a fresh Bash process starting in `$srcdir`. Files in the workspace persist, but changed directories, shell options, and variables assigned during a previous stage do not. Recipes must explicitly change directory again where needed; auxiliary functions remain available in every stage.

### Failures and tests

Bash starts each stage with `errexit` and `pipefail` enabled. A nonzero stage exit stops the sequence; subsequent stages must not run, and incomplete staging contents must not be published as a valid artifact.

These options follow Bash semantics; they do not detect every failed command. In particular, `errexit` has exceptions for conditions in `if`, `while`, and `until`, commands whose status is inverted with `!`, and non-final commands in `&&` or `||` lists. Calling a function in one of these contexts can also suppress its usual `errexit` behavior. `pipefail` affects pipeline status but does not remove these conditional exceptions. The executor must invoke a stage directly, rather than as a conditional test that suppresses `errexit`; recipe authors must handle failures deliberately inside conditional constructs. See the [Bash manual on the set builtin](https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html).

`check()` runs by default when defined. A future executor option may explicitly disable tests; its CLI spelling is not defined here. When disabled, skip both `check()` and resolution of `checkdepends`. Declaring `checkdepends`, even as an empty list, without defining `check()` is a validation error. Missing `check()` and omitted `checkdepends` are valid.

### Security boundary

The Rust implementation orchestrates validation, dependency resolution, source acquisition and verification, and stage execution. Reading metadata never executes recipe code; stage execution still runs untrusted code, including for project-maintained recipes.

`package()` must write only into staging. This is a recipe contract, not a claim that a shell process enforces filesystem confinement. Bubblewrap is the selected isolation basis, with the required boundary described in [the build environment specification](build-environment.md#isolation-boundary). Detailed mounts, per-stage permissions, and enforcement remain to be designed. Availability of host tools does not establish isolation. Builds must preserve user profiles, shell configuration, and host-managed packages.

Final artifact validation must examine interpreters, loaders, libraries, static link contributions, and required paths against the selected dependency providers and recorded host compatibility. Approved host runtime dependencies, including Nix/NixOS store components, are permitted. Reject unresolved, unapproved, or incompatible runtime requirements; an artifact built against one host is not automatically portable to another distribution.

## Examples

### Out-of-tree build with exact dependency and optional tests

This complete illustrative recipe describes a hypothetical Autotools project. Its URL, all-zero checksum, dependency names, and build behavior are placeholders, not verified downloadable software or existing KPB packages. Replace them with actual sources, hashes, and dependencies before use; checksum validation must never accept the placeholder specially.

```bash
pkgname=example
pkgver=1.2
pkgrel=1
pkgdesc='Illustrative out-of-tree build'
license=('MIT')
arch=('x86_64' 'aarch64')
url='https://example.org'
_source_dir="${pkgname}-${pkgver}"
source=("https://example.org/${_source_dir}.tar.xz")
sha256sums=('0000000000000000000000000000000000000000000000000000000000000000')
depends=('libexample=1.2')
makedepends=('make' 'gcc' 'coreutils')
checkdepends=('python')

prepare() {
    test -f "$srcdir/$_source_dir/configure"
}

build() {
    cd "$builddir"
    "$srcdir/$_source_dir/configure" --prefix="$prefix"
    make
}

check() {
    cd "$builddir"
    make check
}

package() {
    cd "$builddir"
    make DESTDIR="$pkgdir" install
}
```

Both `check()` and `package()` enter `$builddir` again because they do not inherit `build()`'s working directory. If tests are explicitly disabled, `python` is not required through this recipe's `checkdepends`; the exact runtime dependency on `libexample=1.2` remains. Tool names are illustrative logical requirements, with provider mappings determined outside recipe syntax. Real configure/build scripts may require additional declared tools; no undeclared host tools become available merely because they are installed.

### Local source without compilation

Place a file named `message.txt` beside `KPB.recipe`, containing exactly `KPB example` followed by one LF newline, with no BOM or other bytes. Its SHA-256 is the value below. This example stages data only under `$pkgdir/opt/kpb`, omits optional functions, declares the packaging tool dependency, and performs no installation into the host.

```bash
pkgname=example-data
pkgver=1.0
pkgrel=1
pkgdesc='Example data file'
license=('CC0-1.0')
arch=('any')
source=('message.txt')
sha256sums=('5232c5a0940f747ac77bb88561dc5c83dd63464c111c9b456a233c04836b1843')
makedepends=('coreutils')

package() {
    install -Dm644 "$srcdir/message.txt" \
        "$pkgdir$prefix/share/example-data/message.txt"
}
```

The license above describes the example data. Packaging tools such as `install` must be explicitly supplied by a validated host provider or a resolved recipe dependency; their presence on the user's PATH is not a dependency-resolution guarantee.

## Future implementation validation

These are required scenarios for a future parser and executor, not existing or executed KPB tests:

- Reject missing required fields, empty required values/lists, invalid types, names, versions, revisions, and hashes.
- Accept comments, multiline lists, omitted optional dependency lists, and supported references; reject duplicates, unknown fields, forward references, list references, environment lookups, commands, and other unsupported metadata syntax without executing them.
- Validate bare and exact dependencies; reject malformed constraints, detect unresolved dependencies and cycles, and preserve build/runtime/test roles.
- Accept a compatible native architecture or `any`; reject incompatible targets and combinations of `any` with specific architectures.
- Reject source/hash count mismatches, missing local files, failed downloads, checksum mismatches, escaping local symlinks, conflicting source names, and unsafe or conflicting archive entries before recipe functions run.
- Verify automatic extraction and availability of unextracted files; never apply patches implicitly.
- Require `package()`, reject `checkdepends` without `check()`, run tests by default, and skip both test execution and test-only dependency resolution when disabled.
- Verify fresh Bash processes and initial directories, persistence of workspace files, reset of stage-local variables/options, and availability of metadata, auxiliaries, and functions in every stage.
- Verify stage and pipeline failures stop execution; cover conditional `errexit` exceptions rather than promising unconditional failure detection.
- Verify staging-only packaging under Bubblewrap, preservation of the user's environment, acceptance of validated host-bound runtimes, and rejection of unresolved/unapproved/incompatible runtime components.
- With a missing direct or transitive dependency and no buildable recipe, report the requirement/constraint/role/chain and stop before source acquisition or recipe execution, without installing host packages.
- Reuse compatible validated host components; build recipes only for requirements not otherwise satisfied.

The source format and execution contract are approved here. The fixed prefix, dependency composition, discovery settings, and Bubblewrap isolation direction are specified in [build-environment.md](build-environment.md), including additional future validation scenarios. Parser implementation, detailed sandbox policy, provider mappings, runtime validation mechanism, artifact format, and executor CLI design require further implementation decisions.
