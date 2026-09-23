---
name: repository-audit
description: Use when assessing pre-existing repository health, including clean worktrees, without changing code or requiring a governing specification or diff.
---

# Repository Audit

Perform an evidence-based, advisory assessment of pre-existing code. This is
not `$code-review`: it does not require acceptance criteria or changed code.

## Read-only boundary

The reviewer never writes. The host must not modify tracked or source files,
must not leave persisted audit artifacts or findings, and must not stage or
commit. Temporary verification output is permitted only under the isolation
rules below. Do not automatically fix any issue or invoke an edit-capable
implementation. Only `review-audit` may review the audit envelope. If it is
missing, return `BLOCKED`; never substitute a specification, quality, or
generic reviewer.

## Establish and inspect scope

The whole repository is the default scope. Honor a user-selected directory or
concern after validating it. If a selected path is missing or unreadable,
report the limitation and never silently broaden scope. Clean and dirty
worktrees are both valid; a diff is attribution context, not the audit
boundary.

Before code, inspect applicable `AGENTS.md`, README guidance, manifests,
configuration, installation rules, and nearby test conventions. Report any
unavailable instruction evidence as a limitation.

Assess applicable correctness, security, data integrity, error handling,
maintainability, duplication, coupling, naming, tests and test gaps,
configuration, and documentation consistency. A preference without concrete
impact is not a defect.

## Verification evidence

Discover safe checks from project evidence. The host may run a permitted check
only when it is known to be non-destructive. If it normally generates caches,
coverage, snapshots, build products, or other files, every output must be
isolated or redirected to temporary output outside the workspace. If those
guarantees cannot be established, skip the check and list it under
**Unobserved recommendations** with the reason.

For every executed check, preserve its exact command, exit result, and decisive
output under **Observed verification**. Never describe an unobserved check as
passing or treat its unavailability as a defect. Verification must not modify
tracked or source files and must not leave persisted audit artifacts.

## Dedicated review

Send `review-audit` a self-contained audit envelope containing the declared
workspace root; selected scope and concern; worktree state; a list of
explicitly named files the reviewer may inspect; located relevant source,
configuration, and instruction excerpts; observed verification; unobserved
recommendations; and known limitations. Every named path and excerpt location
must resolve within the declared workspace root. Files the reviewer may inspect
must also resolve within the selected scope; an applicable instruction excerpt
from an ancestor remains context, not an expansion of audit scope. Missing or
inconsistent evidence, scope, or reviewer availability must return `BLOCKED`.

The native reviewer has no separate file/search tools. Its only
evidence-access route is the command runner in its read-only sandbox, limited
to tightly bounded read-only inspection commands (`pwd -P`, `realpath`,
`sed -n`, and `rg -n`). It may inspect only explicitly named source or
configuration files within the selected scope and applicable instruction files
named in the envelope and located within the declared workspace root. It must
not discover new paths, broaden scope, run verification, or use the command
runner for any mutation.

Order concrete defects by Important, Minor, then Nitpick. Put optional
improvements in a separate section. Assign stable root-cause-based `AUDIT-*`
IDs derived from finding kind, concern or invariant, path, and root-cause
identity—not a line number alone. Each item includes kind, location when
verifiable, evidence, impact, and a minimal located remedy. State any location
limitation rather than fabricating precision.

Use this report schema so evidence limitations remain visible:

1. **Scope and coverage**
2. **Observed verification**
3. **Unobserved recommendations**
4. **Limitations**
5. **Findings**
6. **Optional improvements**, only when supported

If neither a defect nor optional improvement is supported, the Findings
section contains exactly `Findings: NONE`. Keep the preceding scope,
verification, recommendation, and limitation sections in the report; this rule
does not require the whole response to collapse to one line.

```text
## Findings
Findings: NONE
```

## Selection and handoff

Return the report without edits and ask the user to select stable IDs for any
later work. Do not auto-select. A bounded handoff contains only selected IDs,
locations, evidence, impact, minimal remedies, verification observations, and
limitations. Any edit-capable follow-up requires a separate specification and
plan; the audit ends after the handoff.
