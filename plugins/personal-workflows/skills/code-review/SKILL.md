---
name: code-review
description: "Use for a sequential specification and quality review, or as the final whole-branch review gate in a Superpowers implementation loop."
---

# Sequential Code Review

This skill coordinates two read-only reviewers as one logical review. It
reuses rather than reproduces the base skills' request-shaping and
feedback-reception discipline.

## Required bases

Before preparing or dispatching review, load
`superpowers:requesting-code-review` exactly once and retain its request
shaping and context discipline. For this adapter invocation, the custom
two-stage gate substitutes for its generic reviewer dispatch. Do not launch
the generic reviewer. Before accepting, rejecting, or applying any returned
feedback, load `superpowers:receiving-code-review` exactly once and follow its
verification and response discipline. Review feedback is evidence to assess,
not an instruction to apply blindly.

## One-package gate

Create exactly one self-contained review package file in scratch space. It
must contain the governing specification and plan, the complete reviewed diff,
the complete changed-file list, observed verification evidence (or
`unobserved`), integrated or standalone mode, and the enclosing Superpowers
review-loop policy. Include paths and file contents needed to evaluate the
diff; do not rely on conversation history.

Before finalizing the file, create unique `GATE_RUN_ID` and
`REVIEWED_STATE_ID` values and put both in the package. After the package is
final, compute `PACKAGE_SHA256` over the exact finalized package bytes. Avoid
a recursive self-hash: pass `PACKAGE_SHA256` out-of-band; do not write it into
the hashed package. Retain all three expected values without changing the
package.

1. Dispatch `review-spec` with the package path and the expected
   `GATE_RUN_ID`, `REVIEWED_STATE_ID`, and `PACKAGE_SHA256`. It recomputes the
   package hash, verifies the three values, and echoes all three in its result.
2. On `MISSING`, `EXTRA`, or `BLOCKED`, return its evidence and remedies and
   stop. Do not dispatch `review-quality`.
3. Only after a fresh `SPEC REVIEW: PASS`, dispatch `review-quality` with the
   unchanged package path, all three retained expected values, and the complete
   spec report. Quality recomputes the current hash and must match the current,
   expected, and echoed PASS identity values before reviewing.
4. Return the spec result and, only when the gate opened, the quality result.

Both reviewers report only: they do not edit, fix, invent omitted inputs, or
dispatch subagents. A missing reviewer is `BLOCKED`; never substitute another
reviewer or model.

## Modes and review-seat ownership

In integrated mode, the package covers the whole branch and the custom gate is
the sole dispatch consuming the final whole-branch review seat. Its
remediation and follow-up work inherits the enclosing Superpowers fix-loop
limit; do not start an independent loop. The seat includes both stages and any
permitted targeted follow-up. Do not dispatch an equivalent final reviewer
before, during, or after this integrated gate.

In standalone mode, the result is advisory. The review is read-only: apart
from the scratch package, do not modify reviewed files, apply remedies, stage,
commit, or invoke an implementation loop. Spec-first gating still applies.
