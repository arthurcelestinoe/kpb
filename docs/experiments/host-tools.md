# Host GCC experiment

Historical evidence recorded on 2026-11-07, not a production provider, recipe executor or package-acceptance test. Current policy is owned by [decisions.md](../decisions.md). This harness predates the selected-root discovery contract: it finds GCC through PATH, so its discovery behavior must not be copied into production.

## Harness

[Python orchestration](../../experiments/host-tools/nix-gcc-probe.py), [Bash payload](../../experiments/host-tools/probe.sh) and [C fixture](../../experiments/host-tools/probe.c) identify an installed Nix GCC wrapper and its explicit `orig-cc` relationship, query registered references and run offered content verification before candidate execution. The explicit Nix CLI uses the local daemon/offline store; NAR content checks do not establish signature trust. Python, Bubblewrap, the provider CLI and host package database are trusted foundations of this experiment.

The payload uses read-only selected output directories, private workspace/tmp and separate namespaces without home/provider sockets or external network. It checks identity, capabilities, namespace/environment/mount boundaries, compiles/links/runs a C fixture, inspects ELF and rechecks selected input identities afterward.

## Recorded results

| Scenario | Recorded result |
|---|---|
| Native x86_64 NixOS, GCC 16.2.0 | Compile/link/execute passed; fixture reported host glibc 2.44. |
| Registered compiler references | 27 existing output roots; 406,737,104 NAR bytes verified. |
| Structured package version | Unavailable because the local derivation was absent; basename not treated as authoritative metadata. |
| Integrity/isolation checks | Passed for the selected inputs and fixture. |
| Unowned PATH shadow | Rejected before candidate execution. |
| Requested version `999.0.0` | Rejected before compilation. |
| Fake Nix on PATH / inherited `NIX_REMOTE` | Did not replace explicit system CLI/local daemon. |
| Missing candidate | Stopped with a diagnostic before fixture execution. |
| Package acceptance | Not performed; recorded `package_accepted=false`. |

Disposable outputs were recorded under `/tmp/kpb-host-policy-accepted/`, `/tmp/kpb-host-tool-local-mismatch/` and `/tmp/kpb-host-tool-provider-isolation/`; their continued availability is not guaranteed. No host package/profile/database changes or tool downloads were performed by the experiment.

This is not evidence for production candidate grouping/selection, FHS adapters, crate/parser compatibility, real integrity-failure handling, descendant cleanup or general package/runtime acceptance. Claude's later scratch prototype was reported but not reproduced as a repository test. No claim of an archived private-glibc build is made.

## Reproduction

Requires existing Nix, Python 3.11+, GCC on PATH and an explicit Bubblewrap executable. Helpers must be unambiguous members of the selected compiler's registered references. The harness supports this Nix wrapper layout only and stops on missing/ambiguous support.

```sh
/path/to/python3 experiments/host-tools/nix-gcc-probe.py \
  --expected-version 16.2.0 --bwrap /absolute/path/to/bwrap \
  --workdir /tmp/kpb-host-tool-new --run
```

Use a new directory and the actual expected installed version; preserve logs/manifests. Without `--run`, the harness prepares the verified plan only. A failure never authorizes weaker isolation or installing tools.
