<!-- personal-workflows:start -->
## Personal workflow routing

- When a personal adapter and its Superpowers base both apply, use the personal adapter.
- The adapter must load and follow the current Superpowers skill, add only its documented extensions, and never run the base workflow twice.
- If the personal adapter is unavailable, explicitly select and load the applicable skill from the supplied `superpowers:*` catalog. When that skill is present in the catalog, do not claim that it is missing or unavailable.

## Managed model routing

These owned values are the runtime model roles used by `spec-implement`:

- `full`: `gpt-6.1-sol`
- `light`: `gpt-6-luna`

Only the marked personal-workflows block may manage these values. A light
request remains subject to the workflow's eligibility and escalation gates.

## Working agreements

- Apply YAGNI and avoid speculative abstractions or single-use wrappers.
- Comments explain intent and tradeoffs, not the next line of code.
- Never swallow errors; handle, contextualize, or rethrow them.
- Remove dead code and follow the nearest project conventions.
- Keep progress updates concise and distinguish verified evidence from inference.

## Mandatory specification approval workflow

Apply this workflow to every implementation request, including features,
bug fixes, refactors, and chores, unless I explicitly waive a named gate.

Read-only questions, explanations, reviews, and investigations do not
require a specification. If an investigation identifies a fix, return
through this workflow before implementing it.

These approval gates govern skill shortcuts and handoffs, including any
Superpowers option to proceed directly or skip questions.

### Stage 1: Scope and design confirmation

- Inspect the repository and relevant evidence.
- Resolve material questions using the interactive clarification rules.
- Present the proposed scope and design, including relevant constraints
  and exclusions.
- Stop and wait for my confirmation.
- Scope and design confirmation authorizes writing the DRAFT
  specification only. It does not approve the specification, authorize
  implementation planning, or authorize implementation.

### Stage 2: DRAFT specification

- Use `personal-workflows:spec-define`.
- Produce the DRAFT specification for the confirmed scope and design.
- Present the specification and its path, when saved.
- Stop and wait for explicit specification approval.
- Do not create the implementation plan in this stage.
- Do not implement in this stage.
- Specification approval authorizes implementation planning only.

### Stage 3: Implementation plan

- Begin only after explicit approval of the specification.
- Use `personal-workflows:spec-plan`.
- Produce a separate implementation plan grounded in the approved
  specification and current repository evidence.
- Present the implementation plan and its path, when saved.
- Stop and wait for explicit plan approval.
- Do not implement in this stage.
- Plan approval authorizes implementation of the approved scope,
  subject to the Git workflow below.

### Stage 4: Implementation

- Begin only after the specification and implementation plan have
  both been presented and received separate explicit approvals.
- Before implementation, identify both approved artifacts and the
  messages approving them.
- Ensure both approved artifacts are saved before changing product code.
- Use `personal-workflows:spec-implement` and follow the approved plan.
- If either required approval is missing, resume at the earliest
  incomplete stage.

### Approval interpretation

- Approval applies only to the stage or artifact just presented.
- Answering clarification questions does not approve an artifact.
- "Yes", "continue", "looks good", or "go ahead" advances only the
  pending gate. It never approves an artifact that has not yet been
  presented.
- Never combine specification approval and plan approval into one gate.
- Never create the specification and implementation plan together
  before specification approval.
- A proposed approach or native Plan-mode response does not substitute
  for the required specification and implementation plan.
- Leaving Plan mode or accepting a generic implementation prompt does
  not waive missing gates.
- Do not offer direct implementation before the required approvals.
- Do not interpret "just dive in", "skip the questions", or acceptance
  of a skill shortcut as waiving these approval gates.
- A waiver must explicitly identify the gate being waived.
- Material specification changes require renewed specification approval
  and review of the affected plan before implementation continues.
- Material plan changes require renewed plan approval.
- Preserve the current stage and approval evidence across chat
  resumptions and context compaction. Never infer missing approvals.

### Handoffs and mode changes

At each approval handoff, state:

- The current stage.
- The artifact or proposal being reviewed.
- Exactly what approval will authorize.

Then end the turn and wait.

Follow the active mode's tool and filesystem restrictions. If the mode
does not permit saving an artifact, present it in chat and explain the
mode change needed to save it. Do not claim that an unsaved file exists.

A mode change does not change the workflow stage or authorize work
beyond the approvals already given.

## Specification and plan naming

- New specification/plan pairs use the same `YYYY-MM-DD-<slug>.md` basename
  in `docs/superpowers/specs/` and `docs/superpowers/plans/`; omit `-design`
  for new specifications.
- Use the specification's original creation date in both filenames, even
  when planning happens later. Revisions keep the filenames stable.
- Each new document records its own `Created` and `Updated` dates. Preserve
  known Created and update Updated on edits; never invent historical dates.
- Keep shared `Slug` metadata and an explicit `Spec` reference in the plan.
  Resume in another chat by slug or explicit artifact path; use the shared
  artifact-resolution contract and report conflicting evidence before writing.
- Preserve existing filenames and references. A missing plan for an older
  specification reuses that specification's exact basename, including any
  historical suffix. Legacy sources remain read-only.

## Spec-driven Git workflow

1. Do not update `main` or create the implementation branch until the
   specification and implementation plan have both been approved.
2. After those approvals, update `main` safely and create the
   implementation branch. Preserve existing local changes; do not
   discard work or force an update.
3. Use conventional branch prefixes: `feat/`, `fix/`, `refactor/`,
   `chore/`, `docs/`, or `test/`.
4. Work directly in the existing checkout by default. Do not create a
   Git worktree unless I explicitly request one.
5. Keep specification and plan changes uncommitted until the
   implementation branch is created, then commit them on that branch.
6. Implement, verify, and commit on the implementation branch.
7. Do not push or merge unless I request it.

These Git rules take precedence over skill instructions to commit
design artifacts earlier or create a worktree automatically.

## Interactive clarification

Before creating a specification or plan, identify unresolved decisions
that would materially affect the artifact.

1. Check whether the native `request_user_input` capability is available.
2. If unavailable, do not draft the artifact. Ask me to enable Plan mode
   using the Plan command or `/plan`, then reply `continue`.
3. Once available, collect all material clarification through the native
   interactive control before drafting.

When using `request_user_input`:

- Ask one to three short questions at a time.
- Provide two or three mutually exclusive choices.
- Put the recommended choice first and briefly explain each tradeoff.
- Do not include an "Other" option; the client adds the free-form option.
- Wait for my answers before continuing.
- Repeat only while material ambiguities remain.
- Do not ask questions whose answers can be established reliably by
  inspecting the repository.

Clarification answers resolve decisions. They do not replace scope,
specification, or implementation-plan approval.
<!-- personal-workflows:end -->
