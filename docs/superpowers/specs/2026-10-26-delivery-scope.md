# Delivery Scope Specification

**Slug:** `delivery-scope`
**Type:** chore
**Status:** APPROVED
**Created:** 2026-10-26
**Updated:** 2026-10-27
**Provenance:** User's delivery-scoping request, subsequent "Scope/design confirmed; continue", and explicit approval of the separately presented specification in this chat.
**Approval evidence:** The user confirmed scope/design with "Scope/design confirmed; continue". The DRAFT specification was then presented separately and approved by the message beginning "PLEASE IMPLEMENT THIS PLAN:" that reproduces it. This approves implementation planning only; a separate implementation plan and its explicit approval remain required.

This specification was first drafted unsaved in Plan mode on 2026-10-26 and
saved after specification approval in Default mode on the same date. Initial
artifact resolution found no existing specification or plan for this slug.
The builder check found no material unanswered questions. The separately
presented implementation plan was subsequently approved and saved at
`docs/superpowers/plans/2026-10-26-delivery-scope.md`.

## Problem, outcome, and boundary

The existing workflow requires separate scope/design, specification, and implementation-plan approvals. It does not explicitly distinguish an overall project or release direction from the next increment, allowing project-start requests to become a specification and plan for an entire first release before working feedback.

The selected increment integrates delivery scoping across distributed global instructions, the three delivery adapters, shared guidance, documentation, and validation. Its outcome is a verified repository change ready for separately authorized rollout.

Keeping these integrations together allows evaluation of the complete workflow: selecting a scope, specifying it, planning it, executing it, and stopping at its boundary. Distributing the policy alone would leave its application at those stages insufficiently explicit.

Execution ends after implementation, verification, existing final review, local commits, and a handoff containing evidence and rollout instructions. Applying the change to the current Codex installation and refinements informed by later live use remain deferred.

## Delivery scope policy

Adopt the following wording unchanged in the personal-workflows managed global instruction template:

- For new projects and substantial extensions, distinguish the overall
  project/release direction from the next delivery increment.

- During scope/design confirmation, propose the smallest coherent increment
  that produces an independently demonstrable or verifiable outcome.
  State what it delivers, what uncertainty it resolves, what remains
  deferred, and where execution will stop.

- Prefer an end-to-end outcome over separate technical layers. Include
  necessary setup, integration, tests, documentation, and safeguards in
  that increment. A focused fix or chore may already be one increment.

- If later work could reasonably change after evaluating an earlier
  outcome, put it in a later increment. Keep later increments provisional;
  do not write their detailed specifications and plans upfront.

- By default, create one specification/plan pair for the selected increment.
  A project roadmap, release target, or list of future capabilities does
  not authorize their implementation.

- A broader delivery scope is permitted when splitting would undermine
  correctness or create disproportionate overhead. Explain the tradeoff
  and make that broader scope explicit during scope/design confirmation.

- Complete the approved increment autonomously, including its verification
  and review. Then present the working result, evidence, limitations, and
  implications for subsequent work, and stop. Do not automatically begin
  another increment's specification, plan, or implementation.

- Apply the existing approval stages to each subsequent increment.
  Do not add approval gates between ordinary implementation tasks.

- Project-start prompts and handoffs must preserve this distinction:
  describe the wider direction, but identify the first increment as the
  immediate scope.

- Preserve existing approved artifacts and authorization. Propose any
  change to their scope explicitly; do not silently split, invalidate,
  or rewrite them.

## Integration design

The authoritative policy belongs in the [managed global instruction template](../../../plugins/personal-workflows/profile/global-agents-block.md). A shared reference will provide application guidance and examples without duplicating the policy.

Small additions to the delivery adapters will establish these responsibilities:

- **`spec-define`:** explicitly record the selected increment, outcome, uncertainty, deferred work, boundary rationale, and execution endpoint. Distinguish wider direction from immediate scope.
- **`spec-plan`:** keep tasks and verification within the approved specification and state where execution ends. Leave future increments provisional.
- **`spec-implement`:** retain existing execution, verification, and review behavior; report the working result, observed evidence, limitations, and implications; then stop before another increment.
- **`implement-lite`:** retain its existing delegation to `spec-implement`, inheriting the guidance without duplicating implementation behavior.

Guidance for generated project-start prompts will preserve wider direction, immediate first increment, provisional later work, execution boundary, and the actual approval stage. Documentation will include a copyable example. No prompt generator or new skill is introduced.

Existing approved artifacts remain usable even when they lack the newly described scope information. The change does not require metadata backfill or renewed approval merely because this policy was introduced.

The confirmed approach combines managed policy, small adapter additions, and shared examples. Policy-only integration would leave stage-specific behavior less explicit; repeating the complete policy in each adapter would increase drift risk.

## Acceptance criteria

- **AC-01 — Policy ownership:** The supplied policy appears unchanged, once, inside the managed global instruction block.
- **AC-02 — Specification discovery:** New scope proposals and specifications explicitly identify the increment, verifiable outcome, uncertainty, deferred work, boundary rationale, and execution endpoint. Necessary setup, integration, tests, documentation, and safeguards remain included.
- **AC-03 — Proportionate boundaries:** Shared guidance explains coherent end-to-end increments, focused fixes or chores, and justified broader scopes without requiring unnecessary fragmentation.
- **AC-04 — Planning boundary:** Plans remain traceable to the approved scope and state the execution endpoint. Roadmap items do not become detailed future plans or implementation authorization.
- **AC-05 — Completion boundary:** Implementation completes the approved increment, verification, and review; reports results, evidence, limitations, and implications; and stops before subsequent specification, planning, or implementation. Ordinary implementation tasks gain no approval gates.
- **AC-06 — Project-start handoffs:** Generated prompts distinguish wider direction from the immediate first increment, preserve provisional deferrals, and accurately state pending approvals.
- **AC-07 — Existing authorization:** Existing approved specifications and plans remain usable without automatic splitting, rewriting, renaming, migration, invalidation, metadata backfill, or retrospective approval requirements.
- **AC-08 — Workflow compatibility:** Preserve `implement-lite` delegation and existing approval, artifact-resolution, naming, model-routing, review, and Git conventions.
- **AC-09 — Distribution and preservation:** Fresh installation and update distribute the policy. Check mode remains non-writing; reinstall remains idempotent; backups, unrelated guidance, and supported configured model assignments remain preserved. Model-only updates retain the policy.
- **AC-10 — Documentation:** Workflow, installation, README, and changelog documentation explain the behavior, project-start example, compatibility, and supported later rollout procedure.
- **AC-11 — Verification evidence:** Existing repository verification passes. Deterministic contract/distribution results and behavioral observations are reported separately, with actual outputs and limitations.
- **AC-12 — Authorized execution:** Changes remain within this repository and the approved scope. Complete review and local commits in the existing checkout after both artifact approvals. Do not update the current installation, push, merge, or create a worktree.

## Validation

Use existing unittest, temporary-home, fake-Codex, and repository-verifier conventions. Extend focused coverage for policy ownership and adapter integration, fresh installation, upgrade, check mode, backups, idempotence, outside guidance, configured models, and model-only updates. Installer logic changes are not expected; existing mechanisms should carry the policy.

Behavioral evaluation will use frozen baseline and revised instructions with fresh-context agents, common scenarios, recorded outputs, and manual assessment. Establish the baseline before skill edits and follow the applicable skill-writing evaluation requirements.

| Scenario | Required observable behavior |
|---|---|
| New project with several capabilities | Propose a coherent first outcome and defer work that could change after evaluating it. |
| Small focused fix or chore | Keep the work together when it already forms one useful increment. |
| Tightly coupled capability | Permit broader scope with an explicit correctness or disproportionate-overhead rationale. |
| Project-start prompt for another chat | Separate direction and immediate increment; preserve the execution boundary and pending approvals. |
| Existing approved specification and plan | Resume authorized scope without automatic migration, splitting, or retrospective requirements. |
| Completed increment with roadmap work remaining | Finish current verification and review, report results and implications, then stop. |

Assess whether necessary safeguards remain included and whether roadmap work is mistakenly executed. Text-presence checks establish distribution contracts; sampled agent behavior does not establish consistent compliance.

## Constraints and approval handoff

Do not introduce dependencies, installation flags, a reusable evaluation platform, custom agents, required new chats, mandatory roadmap artifacts, or arbitrary task, file, code-size, or time limits. Do not modify upstream Superpowers or installed plugin caches.

The eventual handoff will describe the supported bootstrap checks, explicitly authorized update procedure, post-update verification, and loading of revised instructions. It will not execute that rollout.

**Current stage:** Stage 4 completed. The specification and separate plan
were independently approved and saved before product edits. The increment
passed repository verification and the sequential specification/quality review.
Installation rollout remains a later, explicitly authorized step; evidence
and limitations are recorded in the implementation plan.
