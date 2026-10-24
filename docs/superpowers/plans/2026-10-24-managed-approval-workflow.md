# Managed Approval Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Distribute the approved workflow through bootstrap and align the user's global guidance.

**Architecture:** Expand the existing managed Markdown block. Retain the installer's current ownership boundaries, model preservation, backup behavior, and interfaces. Consolidate the user's global file separately.

**Tech Stack:** Markdown, Python 3.11+, unittest, zsh.

**Spec:** `docs/superpowers/specs/2026-10-24-managed-approval-workflow-design.md`

**Slug:** `managed-approval-workflow`
**Provenance:** Approved specification and native execution selected through interactive clarification.
**Status:** APPROVED
**Approval evidence:** The user separately approved the specification, then explicitly requested implementation of this implementation plan in the message beginning "PLEASE IMPLEMENT THIS PLAN:" and reproducing this plan.
**Execution method:** Native, through `personal-workflows:spec-implement` and its executing-plans base.
**Execution tier:** full
**Implementation model role:** full

The full tier reflects the live-file data risk in Task 2. Native execution retains the current session model.

## Global Constraints and Evidence

- Preserve all supplied wording and section order; relocate only the closing ownership marker and necessary surrounding newlines.
- Preserve unrelated guidance and supported custom model assignments.
- Add no installation flag, dependency, optional profile, or automatic migration of outside copies.
- Automated tests use temporary homes. Only the explicitly authorized local alignment changes live Codex state.
- Do not edit installed plugin caches, other live configuration, or Superpowers.
- Use the existing checkout. Do not create a worktree, push, or merge the implementation branch.
- Repository evidence: `main` at `6ad71b716b4a809ce5dbc37af665da6460b4e261`. No architecture map or ADRs are present; none will be generated.
- Baseline `zsh scripts/verify.zsh` passed: 80 repository tests and 68 plugin tests, plus the remaining verifier checks. Test commands below come from that script.

## Review Focus

1. Missing approval-stage instructions must fail the guidance contract check.
2. Existing outside copies must remain untouched by the general installer.
3. Model-only updates must preserve every expanded workflow instruction.
4. Bootstrap checks must detect drift within the new workflow sections.
5. Local consolidation must preserve unexpected edits and never overwrite an existing backup.

### Task 1: Distribute and verify the complete workflow [size: M | risk: none | mechanical: true | clear_pattern: true | objectively_verifiable: true | concerns: none]

**Acceptance criteria:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-10.

**Files and responsibilities:**

- Expand `plugins/personal-workflows/profile/global-agents-block.md`.
- Extend the existing plugin contract and profile installer test modules, plus repository bootstrap, provider-configuration, and uninstall test modules.
- Update the README, workflow guide, installation guide, and Unreleased changelog entry.

**Interfaces:** Continue using the existing `install_profile`, `merge_managed_block`, model-routing update, and uninstall interfaces. No runtime API or CLI changes are planned.

- [x] **Establish the implementation branch after approval.** Leave Plan mode, save this approved plan, and verify both approval messages and artifacts. Preserve local changes, fetch `origin`, fast-forward `main` safely, then create `chore/managed-approval-workflow`. Stop on a conflict or unsafe update; do not reset or force.
- [x] **Add regression coverage before changing the template.** Use the existing test classes and temporary-home helpers. Cover the following assertions:

  | Scenario | Required result |
  |---|---|
  | Guidance contract | All supplied section headings occur once inside the markers; separate specification and plan approvals remain explicit. |
  | Fresh installation | Installed guidance equals the complete packaged block. |
  | Upgrade from the previous block | New workflow appears; unrelated prefix and suffix remain identical. |
  | Exact outside copy | Outside copy remains unchanged, even when the managed block contains the same rules. |
  | Repeated installation and check | Guidance remains identical, reports `unchanged`, and creates no additional backup. |
  | Custom models | Both selected roles survive installation, checking, and reinstall. |
  | Model-only update | Complete guidance equals its prior content with only the two role values replaced. |
  | Workflow drift | Changing an approval instruction causes bootstrap check to report guidance drift. |
  | Uninstall | Expanded managed guidance disappears; outside guidance remains identical. |

  The guidance contract must include assertions equivalent to:

  ```python
  self.assertIn("### Stage 4: Implementation", managed)
  self.assertIn("Never combine specification approval and plan approval into one gate.", managed)
  self.assertIn("If unavailable, do not draft the artifact.", managed)
  self.assertLess(managed.index("## Interactive clarification"), managed.index(END))
  ```

- [x] **Verify the new contract test fails.** Run `python3 -m unittest discover -s plugins/personal-workflows/tests -v`. Expect failure because the packaged guidance lacks the mandatory sections.
- [x] **Expand the template.** Use the original supplied text, moving the existing end marker after its final clarification paragraph. Compare the result against that source transformation to verify wording preservation. Keep installer and configuration implementations unchanged unless a regression demonstrates a specification violation.
- [x] **Document the lifecycle.** Explain the mandatory defaults, separate approval stages, preserved outside guidance and models, manual cleanup of existing outside copies, and removal of all managed rules during uninstall.
- [x] **Run verification.** Run both unittest discovery commands from the verifier, then `zsh scripts/verify.zsh`. Expect all tests to pass and the final message `Repository verification passed.`
- [x] **Commit the verified repository change and approved artifacts** on the implementation branch with `chore: distribute managed approval workflow`.

### Task 2: Consolidate the global guidance and complete review [size: S | risk: data | mechanical: true | clear_pattern: true | objectively_verifiable: true | concerns: data]

**Acceptance criteria:** AC-09, AC-10.

**Risk:** This task replaces live user guidance. A verified source, exclusive backup creation, and atomic replacement protect against lost edits.

**File:** `/Users/davide/.codex/AGENTS.md`, plus its new sibling backup.

**Interfaces:** Consume Task 1's verified template. Perform a one-time local operation; do not add a migration utility or run the full profile installer against the live home.

- [ ] **Prepare and inspect the local transformation.** Read the current global file, validate its markers, and identify the exact previously supplied outside rules. Render the template with its active model selections. Preserve unrelated prefix and suffix text. Stop rather than remove ambiguous or customized outside instructions.
- [ ] **Validate without changing live state.** Confirm the prepared result contains one managed block and one copy of each workflow section, with the expected model selections and unrelated text. Exercise backup-name collisions and preservation checks using temporary files.
- [ ] **Back up and replace.** Confirm the source has not changed since inspection. Create a collision-safe sibling backup using exclusive creation, preserve file permissions, and replace the global file atomically. Do not modify other live Codex files.
- [ ] **Verify local alignment.** Read the result back and compare it with the prepared content. Verify the backup matches the original bytes and record the backup path. Do not include the backup in Git.
- [ ] **Complete the required integrated review.** Use `personal-workflows:code-review` for the sequential specification and quality review of the complete branch, including verification evidence and local-alignment evidence. Resolve supported findings within the execution workflow; rerun affected checks after changes.
- [ ] **Finish without pushing or merging.** Commit any review corrections or final artifact updates, verify repository status, and report the implementation commit, test results, global-file alignment, and backup location.

## Acceptance Traceability and Handoff

| Criteria | Evidence |
|---|---|
| AC-01–AC-02 | Guidance contract and comparison with the supplied text |
| AC-03–AC-08 | Temporary-home lifecycle, model-routing, and drift tests |
| AC-09 | Local before/after comparison and verified backup |
| AC-10 | Documentation, repository verifier, and final sequential review |

The user approved this plan separately from the specification. Implementation is authorized in Default mode. All material choices are resolved; no further clarification round is planned.
