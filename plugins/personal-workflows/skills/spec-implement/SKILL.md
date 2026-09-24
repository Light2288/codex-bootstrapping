---
name: spec-implement
description: "Use when implementing an approved specification and plan through the selected Superpowers execution workflow, with personal artifact, risk-routing, evidence, and final-review conventions."
---

# Implement an Approved Plan

## Upstream route

Resolve the artifacts and execution choice first. Read and apply the
`spec-implement` execution contract in
[`../../references/integration-map.json`](../../references/integration-map.json).
Then load each selected base exactly once in this order; a base already loaded
by the selected execution workflow is active and must not be loaded again:

1. `superpowers:using-git-worktrees`.
2. Exactly one of `superpowers:executing-plans` or
   `superpowers:subagent-driven-development`, after applying the precedence
   rule below.
3. `superpowers:test-driven-development` during implementation.
4. `superpowers:systematic-debugging` only for an unexpected failure, not an
   intended TDD red.
5. `superpowers:verification-before-completion` before the final gate.
6. After the personal final-review postcondition below,
   `superpowers:finishing-a-development-branch`.

Those bases own worktree setup, task execution or dispatch, TDD mechanics,
debugging mechanics, waits, task review loops, verification, and branch
finishing. Follow them instead of restating or replacing their procedures.

## Personal inputs and routing

Before selecting a specification or plan, read
[`../../references/artifact-resolution.md`](../../references/artifact-resolution.md)
and apply it independently to both artifacts using the same slug. Require the
specification and plan to be approved for implementation. Legacy artifacts are
read-only sources; stop on `CONFLICT` or a missing required artifact.

Choose the execution method from an explicit current user or planning-handoff
choice when present; that choice is authoritative. Otherwise use the approved
plan selection. If multiple non-user sources conflict, stop for resolution
before loading either execution base; always load exactly one.

Use the plan's exact repository-backed build and test commands. If a command
is missing or conflicts with current project configuration, ask for a ruling
rather than inventing a replacement. Retain the exact command, exit status,
and decisive proof line for the final review package; label evidence that was
not observed as `unobserved`.

Interpret each task's `[S|M|L | risk: ...]` metadata without inferring missing
values. Resolve the requested tier from an explicit current entry-point or
user request first, then from the plan's `Execution tier`; a request for
`lite` is not an eligibility override. Use `lite` only when every task is S or
M, `risk: none`, mechanical, grounded in an existing pattern, and objectively
verifiable. Missing or invalid metadata, an L task, any non-`none` risk,
ambiguous or borderline work, and security, auth, data, migration,
concurrency, or performance concerns select or escalate to `full`. Record the
selected tier and every conservative escalation.

Resolve the exact model from the active personal-workflows managed model
routing block. Its default role mapping is `light` = `gpt-5.6-luna` and
`full` = `gpt-5.6-sol`, as recorded in the integration map. For
subagent-driven implementation, every eligible `lite` implementer dispatch
must explicitly set the resolved `light` model; every `full` dispatch and
every escalated or replacement implementer dispatch must explicitly set the
resolved `full` model. With the shipped managed values, those exact dispatch
models are `gpt-5.6-luna` and `gpt-5.6-sol`, respectively. Also pass the
reasoning effort selected under the base's Model Selection rules explicitly.
Never omit either override and never claim a different exact model was
selected.

Inline execution cannot switch the current parent model. Before inline work,
report the selected tier and that no model switch occurred; do not claim model
savings or that the parent is running the managed tier model. Continue with
the selected inline base unchanged. Do not install or simulate legacy
implementer agents.

## Personal final-review postcondition

Preserve the selected base's task loop. In particular, subagent-driven
execution must retain its per-task reviews. When either execution base reaches
its broad final review, invoke `$code-review` exactly once in integrated mode
as the sole final whole-branch review seat. It substitutes for that base's
generic final reviewer: never dispatch a generic final reviewer before,
during, or after it. Its two stages and any permitted targeted follow-up remain
one seat and inherit the enclosing base's fix-loop limit.

The review route is independent of the implementation tier: `review-spec`
performs specification adherence on `gpt-5.6-luna`, then `review-quality`
owns the final code-quality, security, and production-risk judgment on
`gpt-5.6-sol`. Never route that second-stage judgment to the light model.

Only after that gate is passed or its findings are handled under the enclosing
base policy may branch finishing begin. `code-review` is this wrapper's
personal postcondition, not an additional Superpowers dependency.
