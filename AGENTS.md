# Agent instructions

## Before working

1. Read [CONTEXT.md](CONTEXT.md) for project status and documentation ownership.
2. Read [docs/decisions.md](docs/decisions.md) and the specification relevant to the task.
3. Check [open decisions](docs/deferred-decisions.md) for prerequisites of the proposed feature.
4. Inspect the implementation before changing it. Approved requirements are not evidence of implemented behavior.

## Mandatory decision gate

If required architectural behavior is undecided, **stop the affected implementation, ask the maintainer for the necessary decision, and document the agreed solution before resuming**. Do not invent a default, bypass validation/isolation, hide the gap behind a stub, or silently expand scope.

- Identify the open decision ID, dependent feature, missing choice and recommended solution with its trade-offs. Add an ID for a genuinely new architectural gap.
- Bundle only the decisions necessary for the task into one review. Do not ask unrelated deferred questions.
- Use decisions already authorized in the session without requesting approval again. Routine internal names, compatible locked dependency releases and refactoring within an approved contract are implementation choices.
- Continue independent authorized work only when it does not prejudge or bypass the unresolved behavior.
- Before resuming, update the owning decision/specification with scope, rationale, interfaces, failure behavior and required validation; mark the open entry decided with a link.
- If an approved approach proves infeasible, report the specific conflict and request only the necessary amendment.

## Implementation and verification

- Prefer small, focused changes, explicit error handling and actionable diagnostics. Avoid speculative dependencies, abstractions and unrelated refactoring.
- Keep provider-specific commands and identifiers outside the resolver/domain layer.
- Treat recipes, source files and build functions as untrusted. Never execute recipe code with elevated privileges or weaken the approved isolation boundary.
- Preserve host-managed files, profiles, shell configuration and package databases. Tests must be isolated and non-destructive; do not install into system directories without explicit authorization.
- Run relevant checks, review the diff, and report what changed, what was actually tested, and remaining limitations. Never claim an unexecuted test passed or call an operation atomic without implementation evidence.
- Human review remains authoritative for architecture, dependencies, formats, security policy, breaking changes and releases.

## Documentation maintenance

Documentation is in English. Follow the ownership table in `CONTEXT.md`:

- Update each decision in its owning document; reference it elsewhere instead of copying its rules.
- Keep `CONTEXT.md` limited to purpose, implementation status and navigation.
- Keep this file limited to agent workflow. Do not repeat project architecture here.
- Distinguish approved requirements, open decisions, implemented features and experimental evidence.
- Existing P01–P08, A01–A07, B01–B03 and C01–C03 approvals are consolidated in `docs/decisions.md`; keep amendments in that owning document instead of creating competing contracts.
