# Personal Workflows

`personal-workflows` extends Superpowers with the following fourteen skills.

| Area | Skills |
| --- | --- |
| Specification delivery | `spec-define`, `spec-plan`, `spec-implement`, `implement-lite` |
| Review and debugging | `code-review`, `debug`, `repository-audit` |
| Architecture | `arch-map`, `arch-compare`, `arch-design` |
| Documents | `doc-ingest`, `doc-analyze`, `doc-estimate`, `doc-summarize` |

The distribution also contains five managed Codex profiles:
`doc-analyst`, `document-worker`, `review-audit`, `review-quality`, and
`review-spec`.

Each skill has its own `SKILL.md` with invocation guidance and constraints.
The workflow plugin adds routing guidance only through a marked block in a
Codex `AGENTS.md`; it leaves unrelated guidance intact. The five profiles are
read-only reviewers or document workers and are installed only when the
profile installer is explicitly run.

The plugin depends on Superpowers at runtime. Install Superpowers through its
configured marketplace before using these workflows.

`spec-plan` records an execution tier and managed implementation-model role.
`spec-implement` uses `gpt-5.6-luna` only for eligible light subagent work and
uses `gpt-5.6-sol` for full or escalated subagent work by default.
`$implement-lite` is a thin light-route request; it cannot bypass eligibility
or escalation. Inline execution cannot change the current parent model. The
final review uses the configurable light role for specification adherence and
the configurable full role for code quality and security; Luna and Sol are the
exact shipped defaults for those roles, not permanently pinned reviewer names.
