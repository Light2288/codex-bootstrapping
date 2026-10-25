# Paired Artifact Naming Specification

**Slug:** `paired-artifact-naming`
**Type:** chore
**Status:** APPROVED
**Created:** 2026-10-25
**Updated:** 2026-10-25
**Provenance:** User-confirmed scope and clarification answers in this chat on October 25, 2026.
**Approval evidence:** The user confirmed the scope with "confirmed". The DRAFT specification was then presented separately and approved by the user message beginning "PLEASE IMPLEMENT THIS PLAN:" that reproduces it. This approves implementation planning only; a separate implementation plan and its approval remain required.

## Problem and Current Behavior

The workflow currently recommends different filename patterns for specifications and plans. Specifications commonly include `-design`, and plans may use a different date or suffix. This makes related artifacts harder to recognize and reference across chats.

Discovery already uses shared `Slug` metadata and explicit specification references. That compatibility must remain.

## Desired Behavior

New specification and plan pairs use an identical basename:

```text
docs/superpowers/specs/YYYY-MM-DD-<slug>.md
docs/superpowers/plans/YYYY-MM-DD-<slug>.md
```

The filename date is the specification's original creation date. Creating the plan later or revising either document does not change that basename. New specifications omit the `-design` suffix.

Each newly created document records its own `Created` and `Updated` dates. A plan created later therefore has a later `Created` date while retaining the specification's date in its filename. Subsequent edits preserve `Created` and update `Updated`.

Both documents retain shared `Slug` metadata. Plans retain an explicit `Spec` reference.

Existing artifacts keep their names and references. When creating a missing plan for an existing specification, reuse that specification's exact basename, including historical suffixes.

## Acceptance Criteria

- **AC-01 — Shared naming:** Newly originated pairs use the same `YYYY-MM-DD-<slug>.md` basename, without `-design`.
- **AC-02 — Stable date:** The plan inherits the specification's original filename date, including when authored on a later day. Revisions do not rename either artifact.
- **AC-03 — Document dates:** Newly created artifacts contain document-specific `Created` and `Updated` dates. Historical dates are never invented.
- **AC-04 — Reliable references:** Shared `Slug` metadata and the plan's explicit `Spec` reference remain authoritative for pairing. A later chat can resume work using a slug or explicit artifact path without requiring filenames to match.
- **AC-05 — Historical compatibility:** Existing files and references remain unchanged. A new plan for an older specification adopts that specification's existing basename. Existing legacy-location protections remain in force.
- **AC-06 — Ambiguity handling:** Duplicate candidates, contradictory metadata, or a requested new path that conflicts with the naming convention are surfaced for resolution. The workflow does not guess, overwrite, or silently rename.
- **AC-07 — Workflow consistency:** The shared artifact-resolution contract, relevant adapters, packaged global guidance, and documentation describe the same convention and explain how to resume work in another chat.
- **AC-08 — Global alignment:** Update `/Users/davide/.codex/AGENTS.md` with the naming guidance, preserving active model selections, existing ownership-marker boundaries, and unrelated content. Create a collision-safe backup, detect intervening edits, and verify the replacement.
- **AC-09 — Verification:** Add focused contract and behavioral coverage for naming, delayed planning, historical compatibility, and resolution conflicts. The repository verifier passes. Automated checks use temporary files and homes.

## Constraints and Exclusions

- No bulk renaming, reference migration, new installation flag, dependency, or artifact-management command.
- Preserve the current resolution outcomes, conflict safeguards, and legacy read-only behavior.
- Update repository sources and the explicitly authorized global guidance file. Installed plugin caches, Superpowers, credentials, and other live configuration remain outside scope.
- Preserve the separate specification and implementation-plan approval gates and existing Git workflow.

## Verification Scenarios

Verify a same-day pair, a plan created on a later date, and later revisions. Verify a missing plan for a historical `-design.md` specification and lookup of an existing pair with different names.

Exercise resumption by slug and explicit path, plus ambiguous candidates and conflicting requested filenames. Verify live-file preparation and backup collision handling using temporary files before the authorized global update.

## Approval and Handoff

The specification is saved and approved. The current stage is Stage 3: create a separate implementation plan and present it for explicit approval. Implementation is not yet authorized.
