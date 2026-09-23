---
name: debug
description: "Use for evidence-first investigation of unexpected failures, either as a standalone read-only diagnosis or an integrated regression-test and fix workflow."
---

# Debug an Unexpected Failure

**REQUIRED BASE:** Load `superpowers:systematic-debugging` exactly once before
anything else, then follow it. It owns reproduction, isolation, comparison,
data-flow tracing, hypothesis testing, and root-cause discipline; do not copy
or bypass those mechanics here.

## Select one mode

**Standalone investigation** applies when the request is to diagnose or
explain without implementing a fix. Remain read-only: use only non-mutating
commands to inspect and reproduce; do not edit files, add a regression test,
or apply a fix. Return the evidenced cause and decisive observations, or the
escalation record below.

**Integrated fix** applies when an active implementation workflow delegates an
unexpected failure. After the base establishes the cause with evidence, add a
regression test and observe the intended failure before changing production
code. Apply only the causal fix, run the enclosing plan's affected and full
verification commands, and return the exact evidence to the caller. The outer
implementation workflow retains ownership of task review and completion.

An intended first TDD failure is not an unexpected failure and does not enter
this wrapper.

## Bounded escalation

Stop after three distinct evidence-producing hypothesis cycles without an
established cause; retries of the same experiment do not reset the bound. Do
not guess or continue an integrated implementation. Return the reproduction
record, hypotheses and observations, ruled-out alternatives, remaining
uncertainty, and the user or caller decision needed to proceed.
