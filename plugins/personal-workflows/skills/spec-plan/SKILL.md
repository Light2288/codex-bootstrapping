---
name: spec-plan
description: "Use when turning an approved specification or multi-step requirement into an implementation plan, before touching code; extends the Superpowers planning phase with personal project conventions."
---

# Plan an Approved Specification

**REQUIRED BASE:** Load `superpowers:writing-plans` exactly once before doing
anything else, then follow it. Do not reproduce or replace its plan header,
task decomposition, checkbox steps, TDD detail, self-review, or execution
handoff.

## Explicit no-write request

If the user explicitly forbids artifact writes, take the read-only route.
Perform only permitted discovery and shared artifact resolution. Present the
proposed canonical path and plan content in chat, or report the
`MISSING`/`CONFLICT` state and request user selection for `CONFLICT`. Do not
create or update a file, change lifecycle metadata, commit, or claim that the
proposed artifact was created or exists.
Stop after the presentation; this condition replaces only write/commit steps,
not the base's read-only discovery, planning, review, or handoff gates.

## Mission and boundary

Produce only the implementation plan. Read the specification and repository,
and use non-mutating discovery commands, but do not implement, edit product
files, or run mutating project commands. Writes are limited to the new-path
plan and, after approval, lifecycle metadata on a new-path specification.

Before selecting a spec or existing plan, read
[`../../references/artifact-resolution.md`](../../references/artifact-resolution.md)
and apply it. Legacy artifacts remain read-only; new plans and revisions use
the Superpowers location and record `Slug` and `Provenance` metadata.

## Personal planning delta

Keep every field in the Superpowers plan header and its checkbox task format.
Add an execution-tier selection and append this metadata to every task
heading:

`[<S|M|L> | risk: <none|security|data|concurrency|migrations|other>]`

Size is delivery effort; risk is the one material review domain. Explain any
non-`none` risk and split tasks that combine materially different risk
domains. Select `lite` only when every task is S or M, every risk is
`none`, the work is mechanical, existing patterns are clear, and verification
is objective. Otherwise select `full`; borderline work is `full`.

Record the selection once in the plan header, using these exact fields:

- `**Execution tier:** lite` and `**Implementation model role:** light`; or
- `**Execution tier:** full` and `**Implementation model role:** full`.

The model role is a managed lookup key, not a model name. The implementation
workflow resolves its current exact model. This selection does not replace the
base execution-method handoff.

Maintain criterion traceability:

- retain each spec ID exactly (`AC-01`, `AC-02`, ...);
- add `**Acceptance criteria:** <IDs>` to each task; and
- add one compact criterion-to-task/test table when a criterion spans tasks.

Ground the plan in repository evidence. Record architecture-map path and
freshness (including its HEAD SHA and key-path checks), applicable ADR paths
and statuses, and any unresolved decision or explicit assumption. Accepted
ADRs constrain the plan; proposed ADRs are non-binding. Never regenerate an
architecture map during planning.

Every test, build, and verification command must come from current project
configuration or another cited repository source. Record that evidence and do
not invent commands. Preserve the base's exact command and expected-result
requirements in each checkbox step.
