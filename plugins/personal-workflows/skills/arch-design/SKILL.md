---
name: arch-design
description: Use when evaluating an architectural choice and recording a user-approved MADR with explicit options, tradeoffs, and lifecycle status.
---

# Architecture Design

Evaluate an architectural choice and record it as a MADR only to
`docs/adr/NNNN-<slug>.md`.

## Establish the decision

Before drafting, confirm the scope and context, drivers, constraints,
confirmation criteria, two or three real options with pros and cons, the
user's selected option, and the user's rationale. Ask focused questions for
missing decision inputs. Do not invent a selection or rationale.

Inspect existing ADRs for related, conflicting, or superseded decisions.
Accepted records are binding; Proposed records are advisory. Surface conflicts
before drafting.

## Allocate a collision-safe record

Inspect `docs/adr/NNNN-*.md`, ignore invalid prefixes, and choose the maximum
valid four-digit prefix plus one. Start at `0001` and preserve gaps rather than
filling them. Derive a concise lowercase hyphenated slug. Stop on a full-path
collision; do not overwrite or silently choose another number.

## Lifecycle and explicit approvals

New records start as `Proposed`. Present the complete draft, target path,
tradeoffs, negative consequences, status, and any supersession link. Writing
the approved Proposed draft and promoting it to `Accepted` require separate
explicit approvals. Even when the initial request asks for Accepted status,
first obtain draft approval, write Proposed, and only then request explicit
approval for the status change.

When a decision evolves, create a new ADR that supersedes only the immediate
predecessor. Link that predecessor in metadata and Related Decisions and
explain the change. Do not rewrite or backfill prior records or ancestors.

## MADR content

The approved file must retain all of these sections and fields:

- title; Status, Date, Decision Owners, and Supersedes metadata;
- Context and Decision Drivers;
- Considered Options with Pros and Cons for every option;
- Decision and Rationale;
- Consequences with both Positive Consequences and Negative Consequences;
- Confirmation Criteria;
- Related Decisions; and
- Links to relevant specification, plan, architecture map, or evidence.

Success requires max-plus-one numbering, at least two real options, the user's
selection and rationale, both consequence classes, confirmation criteria, and
correct related-decision links.
