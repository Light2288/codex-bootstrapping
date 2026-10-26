---
name: spec-define
description: "Use when defining specifications before planning or implementation; extends Superpowers for feature, bug, refactor, and chore specification."
---

# Define a Specification

**REQUIRED BASE:** Load `superpowers:brainstorming` exactly once before doing
anything else, then follow it. Do not reproduce or replace its path
classification, discovery, design, approval gates, review, or planning
handoff.

## Explicit no-write request

If the user explicitly forbids artifact writes, take the read-only route.
Perform only permitted discovery and shared artifact resolution. Present the
proposed canonical path and specification content in chat, or report the
`MISSING`/`CONFLICT` state and request user selection for `CONFLICT`. Do not
create or update a file, change lifecycle metadata, commit, or claim that the
proposed artifact was created or exists.
Stop after the presentation; this condition replaces only write/commit steps,
not the base's read-only discovery or design gates.

## Mission and boundary

Produce only the requested specification. Read project files for context, but
do not implement, audit, refactor, or edit product files; make such work the
subject of the spec. Writes are limited to the new-path specification and any
base-required commit containing only that artifact. Stop when the base reaches
an implementation transition.

When this skill was invoked to create a written specification, write it after
the selected base path's design gate even if that path would normally keep a
bounded design in chat. Do not add a second conversation or approval workflow.

## Delivery scope

Before scope/design confirmation, apply
[`../../references/delivery-scope.md`](../../references/delivery-scope.md).
Distinguish wider direction from the selected increment. Record its outcome,
uncertainty, necessary setup/integration/tests/documentation/safeguards,
deferred work, boundary rationale, and execution endpoint in the proposal and
specification. Keep later increments provisional. Use the shared prompt recipe
when generating project-start prompts or handoffs, preserving the actual
approval stage and the stop after completing the increment.

Existing approved artifacts and authorization remain usable without new fields,
automatic splitting, or retrospective approvals. Propose scope changes
explicitly through the existing gates.

## Personal specification delta

Before locating, revising, or writing a spec, read
[`../../references/artifact-resolution.md`](../../references/artifact-resolution.md)
and apply it. Legacy specs are read-only; every new spec or revision uses the
Superpowers path and records its source in provenance.
Use the shared naming contract: a new specification is
`docs/superpowers/specs/YYYY-MM-DD-<slug>.md` without `-design`, using its
original creation date. Preserve its basename on later revisions and report
the path and slug at the approval handoff so a later chat can locate it.

Add these metadata lines without removing base content:

- `**Slug:** \`<slug>\`` for exact artifact lookup.
- `**Type:** feature | bug | refactor | chore`.
- `**Status:** DRAFT | APPROVED`, reflecting the current base approval gate.
- `**Provenance:** <request and any normalized source paths>`.
- `**Created:** YYYY-MM-DD` for this document's actual creation date.
- `**Updated:** YYYY-MM-DD` for its latest edit, initially equal to Created.

Preserve known Created and change Updated on revisions. Apply the shared
contract's historical-date and legacy-revision rules; never invent old dates.

Give every acceptance criterion a stable, sequential ID: `AC-01`, `AC-02`,
and so on. Criteria must be concrete and verifiable.

Include `Problem`, `Current Behavior`, `Desired Outcome`, `Acceptance
Criteria`, `Edge Cases`, `Constraints`, `Out of Scope`, and `Notes` when each
adds information. Omit empty fields; omit `Current Behavior` for a genuinely
new capability. Preserve the user's terms and distinguish stated facts from
assumptions.
