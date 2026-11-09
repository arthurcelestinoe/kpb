# Recipe format

This document owns the approved `KPB.recipe` syntax and stage interface. One file describes one package; PKGBUILD compatibility is not assumed. Architecture, runtime acceptance and initial source coverage are defined in [decisions.md](decisions.md), not by examples here. No parser or executor is implemented yet.

## Metadata syntax

Metadata assignments precede functions. Allow blank lines, `#` comments outside quoted text and parenthesized multiline lists. Assign each field/auxiliary once. Scalar auxiliaries start with `_`, followed by letters/digits/underscores; list auxiliaries are forbidden.

Values are literal text, a positive integer for `pkgrel`, or whitespace-separated text lists (`license=('MIT' 'BSD-2-Clause')`, empty `()`). Single/double quotes and simple unquoted tokens without whitespace/shell metacharacters are allowed; quote URLs and dependency constraints. Commas are not list separators.

Only double-quoted text substitutes `${variable}`, referring to a previously declared scalar field/auxiliary. Insert its text once, without recursive expansion or reinterpretation as shell. Single quotes preserve literals.

Reject command substitutions, backticks, arithmetic, operators, conditionals/loops, implicit environment access, `$variable` shorthand, parameter operators, list/forward/undefined references, duplicate assignments, unknown fields and unsupported syntax/types. Top-level commands are forbidden, including after function definitions. Metadata inspection never sources or executes Bash.

## Fields

| Field | Type | Rule |
|---|---|---|
| `pkgname` | Text | Required; `[a-z0-9][a-z0-9._+-]*`. |
| `pkgver` | Text | Required ASCII upstream version matching `[A-Za-z0-9][A-Za-z0-9._+~:-]*`; no SemVer or ordering requirement. Apply after scalar substitution. |
| `pkgrel` | Integer | Required positive revision for the same upstream version. |
| `pkgdesc` | Text | Required, nonempty. |
| `license` | Text list | Required, nonempty; SPDX where applicable, describing packaged software. |
| `arch` | Text list | Required, nonempty; accepted native architectures or `('any')` alone for architecture-independent content. |
| `url` | Text | Optional project homepage. |
| `source` | Text list | Required, nonempty; HTTPS URLs or recipe-relative files. Execution coverage is narrower than syntax. |
| `sha256sums` | Text list | Required; one 64-digit hexadecimal SHA-256 per source, in the same order. No `SKIP`. |
| `depends` | Text list | Runtime requirements, also available during build; default empty. |
| `makedepends` | Text list | Additional build requirements; default empty. |
| `checkdepends` | Text list | Additional requirements only when tests run; default empty. |

Architecture-specific recipes must match the native host; `any` is not cross-compilation permission. Target coverage is defined in [the milestone](decisions.md#initial-milestone).

### Dependencies

Accept `name` or `name=version`, with the `pkgname`/`pkgver` grammars. Reject unsupported version spelling explicitly, without normalization; quoted literals still require this grammar (`..`, `$(id)`, backslashes and control characters are invalid). Exact matching is textual on upstream version, excluding `pkgrel`: `1.2` differs from `1.2.0`. Reject empty parts, multiple `=`, comparisons, ranges and virtual-provider syntax. Bare names impose no version constraint.

Names are stable KPB identifiers, not native package IDs. Resolution, provider validation, executor/probe edges and composition are defined in [dependency planning](decisions.md#dependency-planning). Recipe-used command declarations and executor-owned requirements follow [command roles](decisions.md#probe-registry-and-command-roles); syntax parsing does not infer Bash command use.

## Sources

Verify all source hashes before any recipe function. Reject missing files, failed acquisition, mismatched hashes/counts or conflicting source basenames. Local paths must remain inside the recipe directory after symlink resolution; absolute paths and escapes are invalid. HTTPS destination names use the final URL-path filename; renaming syntax is unsupported.

The overall format specifies automatic extraction of `.tar`, `.tar.gz` and `.tar.xz` into `srcdir`; other files remain ordinary data with no automatic patching. This extraction and HTTPS acquisition are **deferred**, not initial execution support. [Source coverage](decisions.md#sources-and-execution-coverage) defines the exact initial suffix exclusions and D14/D15 boundaries. Git source checkouts, per-source extraction controls and checksum bypasses are outside this version.

## Stage interface

KPB supplies validated metadata/scalar auxiliaries, list metadata as Bash arrays, all accepted functions and these absolute-path variables:

| Variable | Meaning |
|---|---|
| `recipedir` | Private recipe snapshot and declared auxiliary files. |
| `srcdir` | Verified source workspace and initial directory of every stage. |
| `builddir` | Separate workspace for out-of-tree builds. |
| `pkgdir` | Staging root, initially empty. |
| `prefix` | Intended installation prefix, fixed by [the environment contract](decisions.md#prefix-environment-and-workspace). |

Order: metadata validation and dependency preflight → source verification → `prepare()` → `build()` → `check()` → `package()` → static artifact validation. Extraction belongs to the later source-execution slice.

| Function | Required | Responsibility |
|---|---|---|
| `prepare()` | No | Prepare sources. |
| `build()` | No | Compile/generate contents. |
| `check()` | No | Test before packaging. |
| `package()` | Yes | Place payload in staging, without host installation. |

Definitions use `name() { ... }` without declared parameters. Helper functions beginning with `_` are allowed; other stage names/forms are rejected. Each stage runs directly in a fresh Bash process starting at `srcdir`: files persist, directory/variable/option changes do not. Stage scripts execute only inside the [approved sandbox](decisions.md#bubblewrap-and-resource-limits).

Enable `errexit` and `pipefail`. A nonzero stage exit stops execution and leaves invalid staging. Bash exceptions still apply to conditions (`if`/`while`/`until`), `!`, and non-final `&&`/`||` commands; a function called in such a context can suppress `errexit`. Do not invoke the stage as a conditional test; handle intended conditional failures explicitly. See [Bash's set builtin](https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html).

Run defined `check()` by default. `--skip-checks` skips it and resolution of test-only dependencies, never mandatory probes. Any `checkdepends` declaration, even empty, without `check()` is an error. Omitting both is valid.

Packaging may modify private source/build workspaces for bookkeeping; only files under `pkgdir/opt/kpb` are payload. Do not install into the dependency prefix. [Static acceptance](decisions.md#static-artifact-acceptance) owns per-ELF map naming/runtime checks; no recipe field selects a trusted demo or automatic output execution.

## Examples

### Local data

Place `message.txt` beside the recipe, containing exactly `KPB example` and one LF newline (no BOM). This complete example describes data only; it is not an executed KPB test.

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

### Out-of-tree C build, exact dependency and optional tests

This illustrative recipe assumes `app.c` and a compatible `libexample=1.2` exposing the expected headers/library. They are not supplied packages; replace the placeholder SHA-256 with the real source hash. All-zero hashes receive no special acceptance. The map path follows the installed ELF path, including `opt/kpb/bin`.

```bash
pkgname=example
pkgver=1.2
pkgrel=1
pkgdesc='Illustrative C application'
license=('MIT')
arch=('x86_64')
_source='app.c'
source=("${_source}")
sha256sums=('0000000000000000000000000000000000000000000000000000000000000000')
depends=('libexample=1.2')
makedepends=('gcc' 'coreutils')

build() {
    cd "$builddir"
    mkdir -p "$builddir/kpb-link-maps/opt/kpb/bin"
    gcc -I"$prefix/include" -L"$prefix/lib" \
        -Wl,--enable-new-dtags,-rpath,"$prefix/lib" \
        -Wl,-Map,"$builddir/kpb-link-maps/opt/kpb/bin/example.map" \
        -o example "$srcdir/$_source" -lexample
}

check() {
    cd "$builddir"
    ./example
}

package() {
    install -Dm755 "$builddir/example" "$pkgdir$prefix/bin/example"
}
```

Each function re-establishes its directory. `--skip-checks` disables this recipe's `check()`; the exact library requirement remains. Additional test-only tools, if needed, belong in `checkdepends`. The format also represents Autotools/HTTPS recipes, but the first runnable tool/source coverage does not support them implicitly.
