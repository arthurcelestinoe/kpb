# Required implementation validation

These are future checks for the [approved contract](decisions.md), not executed tests. Historical observations belong only in [experiment records](experiments/host-tools.md).

| Area | Required scenarios |
|---|---|
| Rust/parser | Declared minimum Rust and stable with committed compatible lock; complete AST parsing; reject error/missing nodes, top-level commands and unsupported metadata/function forms without executing them. |
| Project layout | Relative/absolute/canonical recipe paths, invalid parent/name/layout or missing catalog, dependency lookup independent of CWD, whole-catalog errors (including unused entries), read-only `validate` without providers/run creation, and run-root overrides that do not change input lookup. |
| Recipe metadata | Accepted/rejected version spellings including quoted literals and post-substitution values; missing/empty/wrong-type fields, malformed names/versions/hashes/dependencies, duplicate assignments, comments/multiline lists, supported scalar references, undefined/forward/list/environment/command references, native architecture and `any`. |
| Catalog | Defaults/cardinalities/identifier grammars, unknown fields/probes/schema, crossed kind fields, typed parameters, provider-specific packages/discovery, exact selectors, release-specific precedence and equal-specificity ambiguity. |
| Graph | Direct/transitive missing requirements and requiring chains, cycles, exact-version conflicts, enabled/disabled tests, pending recipe-built prerequisites, executor/probe roles and no inferred recipe commands. |
| Composition | Runtime closure without completed dependencies' build-only tools; shared directory ownership; file/link/type/mount conflicts; staging separated from inputs. |
| Discovery | Roots' `bin/` entry points versus transitive duplicate tools; no automatic PATH roots; multi-output complete Binutils candidate set; incomplete/incompatible sets and ambiguity across roots. |
| Evidence | Ownership/wrapper chains, package versus effective versions, unsupported versus failed/denied checks, actual integrity mismatches, contradictions, evidence equivalence and stale/invalid explicit choices. |
| Probes | GCC compile/link/inspect/run; raw compiler with missing startup files rejected; library header/link/runtime checks; prerequisite failures and `--skip-checks` never bypassing probes. |
| Orchestration | Absolute Nix/Bubblewrap paths, absent fixed defaults, no PATH/store substitution, no inherited remote store, trusted input recording, no provider socket/CLI exposed to recipe code. |
| Source coverage | Contained local files/symlinks, source/hash counts and basename collisions; reject HTTPS and the three deferred suffixes; other suffixes remain hashed data. Later extraction/acquisition checks require D14/D15 first. |
| Stage execution | Fresh Bash state and initial directory, persistent files, helpers/arrays, direct stage invocation, `errexit` conditional exceptions, pipeline/stage failure, tests default/disabled and `checkdepends` without `check()`. |
| Isolation | Effective namespaces/nonroot/capabilities/environment, no network/home/session/provider data, read-only dependencies and snapshots, writable private workspaces during packaging, no writable parent alias, fail closed on setup failure. |
| Limits | Effective recorded limits, invalid/unenforceable overrides, timeout cleanup of spawning/reparenting/termination-resistant descendants; no aggregate-quota claim. |
| Artifact validation | Every regular ELF including non-executable-mode DSOs, two ELFs with distinct maps, missing/ambiguous maps, generated transient objects, approved external inputs, link-only libraries versus runtime, unsupported formats, staged `.a` and normal/thin/renamed ar archives versus approved external link-input archives, privileged bits/special files/escaping links. |
| Runtime refinement | Interpreter/NEEDED/RUNPATH/transitive resolution, evidence beyond compiler-reference membership, out-of-plan runtime rejection, wrapper-added unused paths, rejection of RUNPATH `/tmp/evil`, no silent ELF rewriting. |
| Evidence lifecycle | Fresh runs/snapshots/hashes, changed/disappeared inputs before consumers/acceptance, no old-success reuse, failed/interrupted staging invalid, typed JSON reasons and CLI exit statuses. |
| Integration | Local C library/app chain; separate runtime-only sandbox with fixed executable/args/status/output/timeout and no build tools. Static acceptance and integration execution recorded separately. |

Provider tests must use mock adapters with controlled evidence/capability states, or disposable test stores where native verification is required. Simulate integrity mismatches, missing/ambiguous/stale data and contradictory provider evidence without corrupting the real host store/database. Mocked failures are not claims of an observed real-store failure.

Tests must use temporary/private state and leave host packages, profiles, shell configuration and system directories unchanged. Unsupported backend/format scenarios are diagnostics, not successful functional support. Additional provider/platform tests must follow D09 rather than infer FHS support from NixOS results.
