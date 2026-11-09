# Open decisions

The open entries below are not approved defaults or instructions to add features; resolved IDs are retained separately. The [current contract](decisions.md) incorporates P01–P08/A01–A07/B01–B03/C01–C03. The [mandatory decision gate](../AGENTS.md#mandatory-decision-gate) applies only when work needs an unresolved choice; it does not reopen approved decisions or routine implementation choices.

| ID | Decision needed | Dependent functionality / stop trigger |
|---|---|---|
| D01 | Package archive layout, metadata, integrity and import/export validation. | Package files, `pack`, artifact import or binary distribution. Staging is not a standardized package archive. |
| D02 | Installed database/schema, package states, ownership and retained dependencies. | Installed queries, registration, ownership updates or runtime garbage collection. Per-run JSON is not installed state. |
| D03 | Installation/upgrade/removal consistency, interruption recovery, rollback and permissions. | Mutation of a running installation or atomic/transactional/recovery guarantees; requires D02/D04 as applicable. |
| D04 | Host installation/activation layout, privilege boundary and host file conflicts. | Host `/opt/kpb`/system writes, PATH/desktop activation, elevated installation or replacing host-owned files. |
| D05 | Persistent cache validity/keys, snapshots, input lifetime and GC retention. | Cross-run probe/artifact reuse, persistent/binary caches, frozen-input or long-lived store-reference guarantees. |
| D06 | Host-update/ABI impact detection and rebuild policy. | Watchers, installed-package invalidation/rebuild automation or guarantees across host updates/removals. |
| D07 | Broader executable/runtime/probe contracts: scripts, imports, plugins/late loading, static/header-only families and provenance. | Acceptance outside initial native ELF executables/DSOs, new probe families or general runtime-execution/smoke-test policy. Representable metadata alone is insufficient. |
| D08 | Aggregate build quotas, cgroup handling and shared-host scheduling. | Multi-user build services, parallel package scheduling or build-wide CPU/memory/process/disk/DoS containment claims. |
| D09 | Additional backend/platform capability, ownership/integrity, architecture, FHS mounts and provider-neutral resource contracts. | Production PackageKit/Pacman/other adapters or platforms beyond the first NixOS path lacking an agreed contract. Their approved general direction need not be approved again. |
| D10 | Remote recipe repository layout/sync, revisions, priorities, trust and third-party warnings. | Repository add/sync, remote execution/updates, multi-repository conflicts or trust flows. Local hashes do not establish remote trust. |
| D11 | Version ordering/ranges, virtual providers and alternative-version resolution. | Range operators, aliases, automatic version preferences or alternative version trees. |
| D12 | Configurable prefixes, relocation, cross-compilation and more target/toolchain contracts. | Prefix changes/relocation promises, cross-target builds or architecture coverage beyond the initial registry. |
| D13 | External catalogs, automatic mapping updates, extensions and plugin trust. | Remote catalog fetch/merge, mapping auto-updates or external probe code. |
| D14 | HTTPS CA trust/resources, ownership/integrity and proxy/redirect/control-plane resource contract. | Network source acquisition or accepting a host CA resource. |
| D15 | Archive worker executable/runtime closure, launch protocol, containment and limit enforcement. | Isolated archive decoding/extraction. Format-level extraction intent alone does not settle worker resources. |
| D16 | Host/KPB library coexistence, duplicate runtime identities, loader precedence and ABI collisions. | Accepting competing implementations/conflicting identities or search paths; reject the composition until decided. |

## Resolved decisions

| ID | Status | Owning decision |
|---|---|---|
| D17 | Decided by C01 on 2026-11-09. | [Local project layout and whole-catalog validation](decisions.md#local-project-layout). |
| D18 | Decided by C02 on 2026-11-09. | [Recipe version grammar](recipes.md#fields). |

When resolved, retain the ID, mark it decided and link to its owning decision/specification before resuming the dependent implementation. Resolve every relevant prerequisite, not unrelated entries. New architectural gaps receive new IDs; approved scope is not silently weakened.
