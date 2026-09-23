# Personal Workflows

`personal-workflows` extends Superpowers with the following thirteen skills.

| Area | Skills |
| --- | --- |
| Specification delivery | `spec-define`, `spec-plan`, `spec-implement` |
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
