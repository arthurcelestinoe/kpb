# Kobalt Package Builder (KPB)

KPB is an experimental source-based package manager for Linux. It aims to build practical applications from simple recipes while reusing validated host infrastructure to minimize compilation. Git recipe repositories, installation, upgrades, removal and ownership tracking are longer-term goals; rebuilding a distribution is outside the initial scope.

## Current status

The initial milestone is specified but not implemented in Rust. The general catalog/recipe parsers, resolver, host adapters, executor and artifact validator do not exist yet. A trusted Python host-GCC experiment exists under `experiments/host-tools/`; its recorded results do not establish production support.

## Documentation ownership

| Document | Sole responsibility |
|---|---|
| [docs/vision.md](docs/vision.md) | Motivation, long-term direction and non-goals. |
| [docs/decisions.md](docs/decisions.md) | Approved architecture, milestone scope, build/host policy, CLI and acceptance. |
| [docs/recipes.md](docs/recipes.md) | Recipe syntax, fields and stage interface. |
| [docs/dependency-catalog.md](docs/dependency-catalog.md) | Catalog schema, value rules and mapping selectors. |
| [docs/deferred-decisions.md](docs/deferred-decisions.md) | Open decisions and the future features requiring them. |
| [docs/validation.md](docs/validation.md) | Required implementation checks, not claims of passing tests. |
| [docs/experiments/host-tools.md](docs/experiments/host-tools.md) | Historical experiment, recorded results and reproduction. |
| [AGENTS.md](AGENTS.md) | Agent workflow, decision gate and documentation maintenance. |

Read the owning document for a rule. Other documents link to it instead of redefining it. The consolidated contract incorporates approvals P01–P08, A01–A07, B01–B03 and C01–C03; none of those proposals remain pending. D01–D16 remain open; D17–D18 are decided. A new approval changes the owning document before dependent implementation resumes.

KPB is licensed under [GPL version 3 or later](LICENSE).
