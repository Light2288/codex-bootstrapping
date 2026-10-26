# Delivery Scope Guidance

The authoritative policy is `Delivery scope` in the
[managed global guidance](../profile/global-agents-block.md). This reference
helps apply it during discovery, planning, completion, and prompt generation.

## Choosing a boundary

Choose an outcome a user can try or a check can verify. Include the setup,
integration, tests, documentation, and safeguards needed to make that outcome
meaningful. Technical tasks inside that boundary can run autonomously under
the approved plan; they do not each need a new scope approval.

| Situation | Useful boundary | Reason |
|---|---|---|
| A document workbench needs intake, extraction, search, collections, and reports; extraction accuracy is unknown. | Intake through inspectable extraction, with originals preserved and failures visible. | Users can assess accuracy before downstream capabilities are specified. |
| A README verification command points at the wrong directory. | Correct the command and verify it using the established project checks. | The focused chore already produces a complete, verifiable outcome. |
| A new serialization format requires coordinated readers, writers, and compatibility fallback. | Deliver the coordinated format change with compatibility tests. | A writer-only result would create unreadable data; splitting undermines correctness. |

Use correctness and the value of feedback to explain the boundary. Keep a
broader scope when splitting would create disproportionate overhead, and make
that tradeoff explicit at scope/design confirmation. Size estimates help plan
tasks; they do not impose limits on the delivery scope.

## Recording the proposed scope

For a new scope, record this compact structure in the proposal and specification:

- **Wider direction:** the project or release context, when relevant.
- **Selected increment and outcome:** what will work and how it can be demonstrated or verified.
- **Uncertainty:** what evaluating that outcome will teach; state when no material uncertainty applies.
- **Necessary safeguards:** setup, integration, tests, documentation, and protections needed for that outcome.
- **Deferred work:** later capabilities that remain provisional.
- **Boundary rationale:** why this is coherent, including any broader-scope tradeoff.
- **Execution endpoint:** completion obligations and the point where execution stops.

A plan carries forward the approved boundary and endpoint, with tasks and
verification traceable to that scope. Later capabilities can remain short
context notes; detailed specifications and plans await their own scope and
approval stages. A roadmap is context, not an additional task list.

## Project-start prompts and handoffs

When asked to generate a project-start prompt, give the receiving chat these
parts, in order:

1. Wider project/release direction and relevant constraints.
2. The immediate first increment, its demonstrable outcome, and uncertainty.
3. Necessary safeguards and explicitly deferred, provisional capabilities.
4. The execution endpoint: finish the approved increment, verification and
   review, report its result, then stop before the next increment.
5. Actual approval state and the next pending gate. A proposed first increment
   still needs scope/design confirmation; a prompt does not establish approval.

For a handoff of existing approved work, carry the selected artifact paths and
approval evidence instead of presenting a new scope as already authorized.
These are prompt contents, not a requirement to use another chat or create a
roadmap artifact.

## Existing approved work

Use the existing approved specification and plan at their authorized scope,
even when they lack increment fields or cover a broader release. Preserve
their filenames, references, approval evidence, and normal artifact lookup.
There is no automatic migration, metadata backfill, splitting, invalidation,
or retrospective approval requirement. Missing new fields alone do not block
resumption. Normal conflict and approval checks still apply. If a scope change
would help, propose it explicitly through the existing approval workflow.

## Completion report

Finish the approved tasks, required verification, review, and authorized Git
steps before reporting completion. Present:

1. The working result and how to demonstrate or verify it.
2. Observed evidence, separating checks actually run from unobserved claims.
3. Limitations and any remaining uncertainty.
4. Implications for subsequent work, with recommendations kept provisional.
5. The reached execution endpoint and any still-pending integration action.

After that report, stop. Subsequent scope discovery, specification, planning,
or implementation starts only through its own authorized workflow. Finish
current safeguards and review even when the demo already works; roadmap work
does not replace those completion obligations.
