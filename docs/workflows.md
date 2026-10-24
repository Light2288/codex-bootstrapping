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
The workflow plugin manages routing, working agreements, mandatory approval
stages, Git workflow, and interactive clarification through one marked block
in a Codex `AGENTS.md`; it leaves guidance outside that block intact. The five
profiles are read-only reviewers or document workers and are installed only
when the profile installer is explicitly run.

## Mandatory approval stages

Fresh installations and updates include these defaults in the managed block:

1. Inspect the repository, resolve material questions through the native
   interactive control, and confirm the proposed scope and design.
2. Write a DRAFT specification with `spec-define` and wait for explicit
   specification approval.
3. Write a separate implementation plan with `spec-plan` and wait for explicit
   plan approval.
4. Implement the approved scope with `spec-implement` only after both
   artifacts have received their own approvals and have been saved.

Read-only questions, explanations, reviews, and investigations do not require
a specification. A resulting fix returns through the approval stages.
Clarification answers, leaving Plan mode, and generic requests to continue do
not waive approval gates. A waiver must name the gate being waived.

When the native interactive clarification control is unavailable, enable
Plan mode using the Plan command or `/plan`, then reply `continue` before
drafting a specification or plan. Plan mode's filesystem restrictions still
apply: present an unsaved artifact in chat when writes are prohibited, then
save it after leaving Plan mode without treating that mode change as approval.

After specification and plan approval, safely update `main` and create an
implementation branch using `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, or
`test/`. Work in the existing checkout unless a worktree is explicitly
requested. Keep specification and plan changes uncommitted until that branch
exists, then implement, verify, and commit there. Push or merge only when
requested.

## Guidance ownership and updates

The complete workflow is inside `<!-- personal-workflows:start -->` and
`<!-- personal-workflows:end -->`. Installation updates that block while
preserving supported custom full/light model selections and all outside text.
Profile uninstall removes the entire block, including the approval rules.

The installer does not move or delete existing copies of these rules outside
its block. After updating, back up your `AGENTS.md`, compare any outside copies
with the managed rules, and manually remove redundant copies. Retain unrelated
instructions and review customized rules before consolidating them; the
installer will continue preserving them on subsequent runs.

## Runtime and model routing

The plugin depends on Superpowers at runtime. Install Superpowers through its
configured marketplace before using these workflows.

`spec-plan` records an execution tier and managed implementation-model role.
`spec-implement` uses `gpt-6-luna` only for eligible light subagent work and
uses `gpt-6.1-sol` for full or escalated subagent work by default.
`$implement-lite` is a thin light-route request; it cannot bypass eligibility
or escalation. Inline execution cannot change the current parent model. The
final review uses the configurable light role for specification adherence and
the configurable full role for code quality and security; Luna and Sol are the
exact shipped defaults for those roles, not permanently pinned reviewer names.
