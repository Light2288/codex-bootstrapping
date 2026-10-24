# Managed Approval Workflow Specification

**Slug:** `managed-approval-workflow`
**Type:** chore
**Status:** APPROVED
**Provenance:** User-supplied AGENTS.md text and scope confirmed on October 24, 2026; existing `plugins/personal-workflows/profile/global-agents-block.md`.
**Approval evidence:** Scope confirmed by the user message "confirm". The specification was then presented separately and accepted in the user message beginning "PLEASE IMPLEMENT THIS PLAN:" that reproduces it. This approves the specification only; a separate implementation plan and its approval remain required.

## Problem and Current Behavior

Bootstrap currently distributes workflow routing, model assignments, and working agreements through one marked guidance block. The mandatory specification approvals, Git workflow, and interactive clarification rules supplied by the user are outside that block in the global `AGENTS.md`.

Existing installations preserve those outside rules, but fresh installations do not receive them.

## Desired Outcome and Selected Approach

Distribute all supplied guidance as managed defaults through the existing block.

Use the supplied text unchanged except for relocating `<!-- personal-workflows:end -->` from after "Working agreements" to after the final clarification paragraph. Preserve section order and wording. Retain the existing start marker and exactly one end marker.

Fresh installations receive the complete workflow. Updates replace the managed content while retaining supported custom model selections and unrelated outside guidance. Profile uninstall removes the complete managed workflow.

Two alternatives were considered:

- **Optional strict profile:** introduces a separate installation choice; rejected in favor of managed defaults.
- **Automatic migration of outside copies:** changes the installer's ownership boundary; rejected in favor of explicitly consolidating this user's global file.

The general installer continues preserving outside text, including manually copied or customized versions of these rules.

## Acceptance Criteria

- **AC-01 — Complete template:** The packaged managed block contains all supplied sections, including the four approval stages, approval interpretation, handoffs, Git workflow, and interactive clarification rules.
- **AC-02 — Wording:** Existing instructions retain their wording and order. The marker relocation and necessary surrounding newlines are the only content transformation.
- **AC-03 — Fresh installation:** Installing into an empty temporary Codex home produces one complete managed block without duplicate workflow sections.
- **AC-04 — Existing installation:** Updating the previous managed block installs the complete workflow and preserves unrelated prefix and suffix text.
- **AC-05 — Outside copies:** The general installer preserves rules outside its block, including exact copies. Documentation explains that existing outside copies require manual consolidation.
- **AC-06 — Model preservation:** Supported custom full/light assignments survive installation, checks, and repeated installation. Model-only configuration updates preserve the expanded workflow text.
- **AC-07 — Idempotence and checks:** A repeated installation makes no guidance changes. Check mode performs no writes and reports missing or changed managed workflow content through the existing status behavior.
- **AC-08 — Uninstall:** Profile uninstall removes the expanded managed block while retaining unrelated outside guidance.
- **AC-09 — Local alignment:** Explicitly update `/Users/davide/.codex/AGENTS.md` to the expanded managed structure, with one copy of each workflow section. Preserve active model selections and any unrelated guidance, and create a collision-safe backup before replacement. Do not change other live Codex files.
- **AC-10 — Documentation and verification:** Document the managed defaults, update behavior, manual consolidation, and uninstall effect. Add focused regression coverage and pass the repository verifier. Automated tests use temporary homes and do not modify live Codex state.

## Edge Cases

- Existing malformed or duplicate ownership markers retain their current rejection behavior.
- Customized outside guidance remains outside installer ownership.
- Local consolidation must verify the current file before replacement; unexpected edits must be preserved or reported as a conflict.

## Constraints

- Keep the existing installer interface and ownership markers. No new installation flag or dependency is required.
- Preserve existing backup and conflict protections.
- Keep Superpowers, installed plugin caches, provider credentials, and other live configuration outside this change.
- Follow the approved Git workflow: save the approved artifacts before implementation; update `main` and create the implementation branch only after separate specification and plan approvals; do not push or merge.

## Out of Scope

- An optional strict profile or automatic migration of outside copies.
- Changes to other live Codex files, provider credentials, Superpowers, or installed plugin caches.
- Pushing or merging the implementation branch.

## Notes

The user selected managed defaults and local-only cleanup through the native interactive clarification control, then separately confirmed the scope. The specification was first presented in Plan mode and could not be saved then. It is now saved after specification approval in Default mode.

The next stage is creating a separate implementation plan. Specification approval does not authorize implementation. The implementation plan must receive its own explicit approval before product files or the live global guidance are changed.
