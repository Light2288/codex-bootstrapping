# Delivery Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for the user-selected Native execution method. Steps use checkbox syntax for tracking.

**Goal:** Distribute and integrate the approved delivery-scope policy so workflows select a coherent increment, complete it, report evidence, and stop.

**Architecture:** Maintain the policy in managed global guidance, with shared application guidance and small additions to the three delivery adapters. Reuse existing installation mechanisms, tests, model routing, and sequential final review.

**Tech Stack:** Markdown, Python 3.11+ unittest, zsh.

**Spec:** [Approved specification](../specs/2026-10-26-delivery-scope.md)

**Slug:** `delivery-scope`
**Created:** 2026-10-26
**Updated:** 2026-10-27
**Status:** APPROVED
**Approval evidence:** After separate specification approval, the user approved this separately presented plan with the message beginning "PLEASE IMPLEMENT THIS PLAN:" that reproduces the Delivery Scope Implementation Plan. Stage 4 is authorized. The earlier similarly prefixed message reproduced the specification and approved planning only.
**Provenance:** Separately approved specification and native interactive selection of "Native (Recommended)".
**Execution method:** Native, through `personal-workflows:spec-implement` and `superpowers:executing-plans`.
**Execution tier:** full
**Implementation model role:** full

The full tier reflects judgment involved in instruction writing and behavioral assessment. Native execution retains the current session model.

This plan was first drafted unsaved in Plan mode on 2026-10-26 and saved
after its explicit approval in Default mode on the same date.

## Global constraints and repository evidence

- Adopt the specification's policy wording unchanged. Preserve approval, artifact-resolution, naming, delegation, model-routing, review, and Git conventions.
- Preserve existing approved artifacts and authorization without automatic migration, splitting, renaming, metadata backfill, or retrospective approvals.
- Introduce no dependencies, installation flags, reusable evaluation platform, custom agents, required chats or roadmap artifacts, or arbitrary task/file/code/time limits.
- Work in the existing checkout. Do not update the current installation, edit installed caches or upstream Superpowers, create a worktree, push, or merge.
- Inspected `main` at `2b398642b66b9d569cca15e8815f5682bbd3e38f`. The only current change is the uncommitted approved specification.
- Specification resolution: `NEW_ONLY`; plan resolution: `MISSING`. The plan inherits the specification's exact basename.
- Architecture-map path `docs/architecture/map.md` and ADR directory `docs/adr` are absent. Freshness and ADR statuses are therefore unavailable; neither will be generated.
- During planning, `zsh scripts/verify.zsh` exited 0 with `Repository verification passed.`
- Verification commands below come from [the repository verifier](../../../scripts/verify.zsh). The available `python3` is 3.14.7, satisfying its version requirement.

**Execution endpoint:** Complete this repository increment, verification, review, local commits, and evidence handoff. Stop before installation rollout or another increment.

## Review focus

1. Small fixes must remain coherent rather than acquire artificial subdivisions.
2. Necessary integration, tests, documentation, and safeguards must survive scope reduction.
3. A justified broader scope and an existing approved broad scope must remain usable.
4. Generated project-start prompts must preserve both immediate scope and pending approvals.
5. Completion must finish current verification/review while leaving subsequent roadmap work untouched.

Each condition is covered by the behavioral cases below; distribution preservation also receives deterministic coverage.

## Task 1: Integrate and verify delivery scoping [size: M | risk: none | mechanical: false | clear_pattern: true | objectively_verifiable: false | concerns: none]

**Acceptance criteria:** AC-01 through AC-12.

**Files and responsibilities:**

| Surface | Changes |
|---|---|
| Policy and guidance | Modify `plugins/personal-workflows/profile/global-agents-block.md`; create `plugins/personal-workflows/references/delivery-scope.md`. |
| Delivery adapters | Modify `plugins/personal-workflows/skills/{spec-define,spec-plan,spec-implement}/SKILL.md`. |
| Deterministic tests | Extend `plugins/personal-workflows/tests/{test_plugin_contract,test_install_profile}.py` and `tests/test_bootstrap.py`. |
| Documentation | Update `README.md`, `CHANGELOG.md`, `docs/workflows.md`, and `docs/installation.md`. |
| Artifacts and evidence | Save this approved plan at its intended path; record approval and completion evidence in the artifact pair. Preserve other specifications and plans. |

`implement-lite`, model assignments, integration-map routing, installer logic, plugin metadata, and upstream dependencies remain unchanged.

**Interfaces:** Continue using `install_profile(codex_home: Path, plugin_root: Path, check_only: bool) -> dict` and existing bootstrap/test helpers. No runtime API or CLI changes. The added interface is an instruction contract describing scope information and completion reporting.

### Preparation and baseline

- [x] **Establish the approved execution context.** After explicit plan approval and leaving Plan mode, save this plan and identify the two separate artifact-approval messages. Preserve local changes, fetch `origin`, safely fast-forward `main`, and create `chore/delivery-scope`. Stop on an unsafe update, conflicting upstream changes, or branch collision; do not reset or force. Commit the approved artifacts on that branch with `chore: record approved delivery scope artifacts`.
- [x] **Initialize the Native execution ledger** using the selected base workflow. Record the starting commit, artifact identities, execution endpoint, and `Pre-flight: no shared interfaces` for this single task.
- [x] **Freeze behavioral inputs before instruction edits.** Retain the baseline managed guidance, adapters, shared artifact-resolution contract, and applicable base instructions in this plan's scratch workspace. Prepare the six scenario inputs below and a separate assessment rubric. Evaluators receive the relevant instructions and realistic request, without expected answers or this chat's policy discussion.

### Deterministic RED checks

- [x] **Add `test_delivery_scope_policy_matches_approved_specification`.** Extract the approved specification's policy bullets and compare them exactly with the managed `## Delivery scope` section. Assert one section inside the ownership markers and preserve existing approval-section assertions.
- [x] **Add `test_delivery_adapters_expose_increment_boundaries`.** Assert that all three adapters link the shared reference and contain their stage-specific recording, endpoint, completion, and compatibility guidance. Check reference links resolve. These assertions establish instruction contracts only.
- [x] **Add `test_delivery_scope_upgrade_preserves_models_and_outside_text`.** Use a temporary home with the pre-policy managed block, custom full/light assignments, unrelated prefix/suffix, and unrelated agent content. Verify non-writing check mode, complete expected installed guidance, exact backup contents, preserved assignments/content, and unchanged bytes/backups after repeated check/install.
- [x] **Extend fresh-install coverage** to assert the exact policy is installed once inside the markers.
- [x] **Add `test_check_rejects_drift_in_delivery_scope_policy`** using the existing bootstrap helper. Remove the policy from an otherwise complete temporary installation; require nonzero check status, a guidance-drift report, no Codex invocation, and unchanged target bytes.
- [x] **Retain existing model-only and bootstrap preservation tests.** Their complete guidance comparisons must continue proving that only configured model assignments change and subsequent checks/reinstallation preserve them.
- [x] **Observe RED.** Run:
  - `python3 -m unittest discover -s plugins/personal-workflows/tests -v`
  - `python3 -m unittest discover -s tests -v`

  Expected: new policy/adapter/distribution assertions fail because the policy is absent; existing unrelated checks remain green. Correct test errors before proceeding.

### Behavioral baseline and instruction changes

- [x] **Run baseline evaluations before skill edits.** Apply `superpowers:writing-skills` and its required background. Use five fresh-context runs of the six-case bundle. Separately exercise two pressure cases: project-start scope expansion under deadline/authority pressure, and roadmap continuation under sunk-cost/efficiency pressure. Prohibit writes and actual implementation.
- [x] **Record actual baseline decisions**, including successes, omissions, rationalizations, and variation. Do not manufacture baseline failures or claim improvement where behavior already satisfies the rubric.
- [x] **Add the managed policy verbatim**, before the existing mandatory approval workflow. Preserve the existing marker pair and every other managed section.
- [x] **Write the shared reference** with:
  - Guidance for choosing an end-to-end boundary, including focused work and justified broader scopes.
  - A compact scope-recording structure: wider direction, selected increment, demonstrable outcome, uncertainty, necessary safeguards, deferrals, boundary rationale, and execution endpoint.
  - A project-start prompt recipe preserving wider direction, immediate scope, provisional future work, stopping point, and actual approval stage.
  - Existing-artifact compatibility and completion-report guidance.

  Reference the managed policy as authoritative rather than repeating its complete wording.
- [x] **Add directly relevant adapter guidance.** `spec-define` uses the reference during scope discovery and records the boundary information. `spec-plan` binds tasks and verification to approved scope and states the endpoint. `spec-implement` preserves execution and review, then reports the outcome, observed evidence, limitations, and implications before stopping. Existing approved artifacts need no new fields or renewed approval solely because of this addition.
- [x] **Update documentation with the same behavior.** Include one copyable project-start prompt separating a wider release direction from a first working outcome. Explain focused fixes, broader-scope exceptions, existing authorization, and the absence of new intra-task gates.

### GREEN verification and behavioral assessment

- [x] **Run the same frozen evaluations against revised instructions.** Use five fresh-context runs of the six-case bundle and repeat the two separate pressure cases. Keep model/effort, scenario wording, and assessment rubric consistent across variants; record any unavoidable difference.

| Case | Concrete fixture | Required revised behavior |
|---|---|---|
| New project | Document intake, extraction, search, and reporting are possible release capabilities; usefulness of extraction is uncertain. | Propose one usable intake-to-review outcome with necessary validation and safeguards; defer feedback-dependent capabilities. |
| Focused chore | Repair one broken documented verification command. | Treat correction and appropriate verification as one increment. |
| Coupled capability | Change a serialization format where reader, writer, and compatibility handling must agree. | Retain a coherent broader scope and explain correctness/overhead reasons. |
| Project-start prompt | Generate a prompt for another chat from a multi-capability release direction; no artifact approvals exist. | Identify the first increment and pending scope/design gate; preserve provisional later work. |
| Approved work | Resume an explicitly approved broader specification and plan lacking increment fields. | Preserve existing artifacts and authorization; do not silently split or demand backfill. |
| Completion | Current functionality is ready, verification/review remain, and later roadmap items are listed. | Finish current checks, report evidence and implications, then stop before subsequent work. |

- [x] **Assess actual outputs manually.** Check boundary quality, retained safeguards, unjustified fragmentation, approval preservation, and unintended roadmap execution. Record sample identities, instruction hashes, model/effort, actual decision excerpts, per-case results, and limitations in this plan's implementation-evidence appendix. Retain decision evidence before normal scratch cleanup.
- [x] **Resolve material observed failures within approved scope.** Keep policy wording unchanged. Refine application guidance and repeat affected evaluations when results justify it. A substantive policy or plan change returns to the corresponding approval gate.
- [x] **Run `zsh scripts/verify.zsh`.** Expected: exit 0 and `Repository verification passed.` This runs both unittest suites and the existing shell, manifest, contract, and secret checks. Record exact status and decisive output.
- [x] **Inspect the complete diff.** Confirm unchanged delegation/routing and unrelated guidance, no live-state or upstream edits, and no modifications to historical artifact pairs. Commit the verified change with `chore: integrate incremental delivery scopes`.

### Final review and handoff

- [x] **Invoke `personal-workflows:code-review` once in integrated mode** as the sole final whole-branch review seat. Supply the approved artifacts, complete diff/file list, Review Focus, deterministic results, behavioral observations, and limitations. Follow its immutable-package identity checks and sequential specification-then-quality gate using the configured light/full roles.
- [x] **Handle supported findings under the Native base's review policy.** Verify affected corrections and record rulings or deferred findings. Do not add a parallel generic final reviewer.
- [x] **Record completion evidence and commit it** with `chore: record delivery scope verification`. Confirm the local branch and repository status.
- [x] **Present the result and stop.** Report commits, changed behavior, deterministic verification, observed behavioral results, limitations, and implications. Include the later rollout procedure: review the intended revision; run bootstrap check/dry-run; after separate authorization run bootstrap, verify installation health, and start a chat that loads the revised guidance. Explain that repository edits or a profile-only refresh do not by themselves refresh installed skill content. Do not perform rollout.

## Acceptance traceability and approval handoff

| Criteria | Implementation and evidence |
|---|---|
| AC-01 | Exact policy comparison and managed-section ownership test |
| AC-02–AC-06 | Shared guidance, adapter additions, project-start example, six cases and pressure evaluations |
| AC-07–AC-08 | Existing-artifact case, unchanged workflow contracts, routing/delegation tests and diff inspection |
| AC-09 | Temporary-home fresh install/upgrade/drift checks and existing model-preservation suites |
| AC-10 | Workflow, installation, README, changelog, and rollout handoff |
| AC-11 | Separately reported deterministic results and observed behavioral evidence; full verifier |
| AC-12 | Approval/branch preparation, repository-only edits, integrated review, local commits, explicit endpoint |

**Current stage:** Stage 4 completed. The user separately approved the
specification and this plan; both were saved before product edits. The increment
is verified, reviewed and committed locally. Installation rollout remains
a later, explicitly authorized step; no subsequent increment has begun.


## Implementation evidence

Separate approval messages reproduced the specification and then this plan.
Both were saved before product edits. `origin` was fetched, `main` was already
current at `2b398642b66b9d569cca15e8815f5682bbd3e38f`, and branch
`chore/delivery-scope` was created in the existing checkout. Approved artifacts
were committed as `e090e8d43342ae430a881122c2bb1118805359c3`.

### Deterministic contracts and distribution

- RED: `python3 -m unittest discover -s plugins/personal-workflows/tests -v`
  exited 1: 77 tests, six assertion failures (including three adapter subtests),
  no errors. Missing policy, adapter links, fresh-install policy, and upgrade
  behavior caused the expected failures.
- RED: `python3 -m unittest discover -s tests -v` exited 1: 82 tests, one
  assertion failure for the missing delivery policy; no errors.
- GREEN: plugin suite exited 0: 77 tests, `OK`.
- `zsh scripts/verify.zsh` exited 0: 82 repository tests and 77 plugin tests,
  both `OK`, followed by `Repository verification passed.` The verifier also
  completed shell, manifest/contract and tracked-secret checks.
- `git diff --check` passed. Removing exactly the added policy restores the
  managed template byte-for-byte to `main`. The installer, artifact-resolution
  contract, integration map, and implement-lite skill match `main` byte-for-byte.
- Tests use temporary homes and fake Codex. Installation, configured model
  preservation, read-only checks, backup contents, idempotence, and policy
  drift detection were exercised without changing the current installation.

These deterministic results establish copy, link, and distribution contracts.
They do not establish agent compliance.

### Behavioral evaluation protocol

Five fresh-context consumers per variant answered the same six independent
synthetic cases. Two additional fresh consumers per variant answered separate
pressure cases. All fourteen used `gpt-6.1-sol`, reasoning effort `high`,
`fork_turns: none`, with read-only instructions. No implementation worker was
dispatched. Inputs excluded this chat and the expected-answer rubric.

The baseline was frozen before instruction edits. Both snapshots included the
managed guidance, delivery adapters, artifact-resolution contract and relevant
upstream brainstorming/planning/execution/finishing instructions. The revised
snapshot additionally included the new shared delivery reference. Both
variants used identical case/prompt wording and output instructions. Runs
crossed midnight from October 26 to October 27; incidental filename dates were
not scored, and all scope/approval facts were fixed in the inputs.

| Frozen input | SHA-256 |
|---|---|
| Baseline instructions | `630f8919a359c25d7cd10fbbb7dc70bbf1ec13a47ce4f17b6428bb2c1b569662` |
| Revised instructions | `f4d6747338507a1f5831da1dcbced17228b8ec8403232c4f23ffc6bf10d196f2` |
| Six-case bundle | `eafdfafb33bd15b6394af2a9e4b02b80bdbf01221596933982a1e82d4755a20f` |
| Project-start pressure | `80d810cbb2aefa41d9c0e3ed118e9e8a1c109c19961820eb76b6b1ad695a6af2` |
| Completion pressure | `3f554d77c5e87a9c560733c6e404ad18cc4858ff14908d2bb2db7f1862bdb139` |

The cases were: new document workbench with uncertain extraction usefulness;
approved README command correction; coordinated serialization readers/writers/
fallback; prompt for another workbench chat without approvals; approved broad
historical workbench artifacts lacking increment fields; and completed
intake/extraction functionality with required tests/docs/review still pending
and search/reports only on a roadmap. Pressure cases added deadline, authority
and payment incentives to project start, and sunk cost, fatigue, deadline and
social/efficiency incentives to completion. The scoring checked useful
boundaries, retained safeguards, approvals, compatibility, stopping behavior,
and explicit reporting fields rather than policy quotation.

### Observed decisions and limitations

All five baseline bundles already chose useful intake/extraction scopes,
kept the focused chore together, retained the coupled format scope, preserved
the approved broader artifacts, and completed current checks without executing
roadmap capabilities. Neither baseline pressure response broadened authorized
work. There was no observed baseline failure of these substantive boundaries;
no improvement on those decisions is claimed.

The observed shaping gap was explicitness: all five baseline project-start
prompts stopped at approval sequencing without saying to stop after the first
completed delivery; baseline completion responses varied in result/evidence/
limitations/implications fields. Revised outputs made post-delivery stopping
explicit in all five prompts. Reporting detail still varied: revised_4's
scope proposal did not spell out the eventual completion endpoint (its handoff
prompt did), and its prompt did not explicitly name implications. These are
recorded omissions, not hidden passes or evidence of consistent compliance.

| Case | Actual baseline excerpt | Actual revised excerpt and assessment |
|---|---|---|
| New project | baseline_1: “first usable workbench covering local PDF intake, text extraction and inspection against the source” | revised_1: “execution ends after this increment is verified, reviewed and reported.” Useful scope in both; revised endpoint more explicit. |
| Focused chore | baseline_2: “replace the README command with the existing verifier's correct command” | revised_2: “without adding task approval gates.” Both kept the chore together and completed verification/review. |
| Coupled capability | baseline_3: “one coherent change covering the versioned format, readers, writers and compatibility fallback” | revised_3: “broader boundary is necessary for correctness.” Both retained the necessary coordinated capability. |
| Project-start prompt | baseline_4: “stopping first for scope/design confirmation; no approvals exist.” | revised_4: “then stop before starting another increment.” Both preserved current approval state; revised prompt also bounded delivery. |
| Existing approved work | baseline_5: “Missing increment fields require no artifact change or renewed approval” | revised_5: “No increment-field backfill, replacement artifacts, splitting, or renewed approvals are required.” Both preserved the broad approved scope. |
| Completion | baseline_1: “working demo does not satisfy those remaining completion requirements” | revised_1: “observed evidence, limitations, provisional implications for later work and pending integration permissions”. Both finished safeguards and stopped; revised reporting was more explicit. |

Sample identities below are the fresh child task names under `/root`. Each
bundle's six decisions was inspected, not scored from keyword counts.

| Sample | Actual excerpt relevant to boundary/reporting |
|---|---|
| baseline_1 | “then stop for the branch integration decision” |
| baseline_2 | “Then present the branch-finishing choice and wait” |
| baseline_3 | “search and reports remain future work requiring their own scope, specification and plan approvals” |
| baseline_4 | “Missing increment fields require no artifact changes or renewed approvals under these instructions.” |
| baseline_5 | “implementation tasks may be separate, but the capability's completion requires all of them” |
| revised_1 | “then stop before starting another increment” |
| revised_2 | “The eventual endpoint is verified, reviewed intake and extraction plus an evidence report, followed by a stop.” |
| revised_3 | “report its working result, evidence, limitations, and implications, then stop before starting another increment” |
| revised_4 | “report the working result, evidence and limitations, then stop before starting another increment” |
| revised_5 | “while keeping search, collections, and reports provisional and deferred” and “then stop before another increment” |
| baseline_pressure_start | “recommend the smallest useful demonstration that tests extraction before committing to dependent capabilities” |
| baseline_pressure_finish | “I do not begin another specification, plan, or chat for search/reporting without a request.” |
| revised_pressure_start | “Keep search, collections, and reports provisional and deferred” and “then stop before starting another increment.” |
| revised_pressure_finish | “I continue these ordinary completion tasks without requesting new scope approvals” and “I stop at that increment's completion”. |

These are simulated choices from one model and a small set of constructed
requests. Bundled cases share a context within each sample. The evaluator knew
it was a read-only exercise; no actual project or deployment was run. The
observations do not prove reliable compliance, statistical improvement, or
live installed-skill behavior. They support the proposed instruction shape,
while the distribution tests independently prove the policy reaches the
managed installation surfaces.


### Integrated review: specification correction

The first specification review returned `SPEC REVIEW: MISSING` for AC-02,
based on the recorded revised_4 proposal omission. It verified package identity:

- GATE_RUN_ID: `90fedc0e-a90a-4f5c-bcc5-e9ad56c71030`
- REVIEWED_STATE_ID: `406f857040bbc57d2278881f1ef4368a0af3316f`
- PACKAGE_SHA256: `6b42674d5617baa906a1a83bc54f96771eebb3933c4227d72925f676414d32b6`

The reviewer found no extra scope or other supported criterion failures.
Quality review was not dispatched on that non-PASS. The located remedy was a
proposal endpoint presence check in spec-define. The one correction pass adds
a required `Execution endpoint:` output line and checks it before presenting
new proposals. The authoritative policy, approvals and historical artifacts
remain unchanged.

The new adapter-slot contract failed RED (77 plugin tests, one assertion
failure, no errors) before the guidance changed. After correction,
`zsh scripts/verify.zsh` exited 0: 82 repository tests, 77 plugin tests, `OK`,
and `Repository verification passed.`

Five additional fresh consumers (`endpoint_fix_1` through `endpoint_fix_5`)
used the same model/effort and fork settings. Each received the corrected
snapshot and only the affected new-project case, rather than the original
six-case bundle; the case facts and neutral decision request were unchanged.
All five included an explicit execution endpoint covering the working
outcome, verification/review, a report and stopping before later work.
Formatting and report-detail variation remain: endpoint_fix_2 put approval
sequencing after the endpoint, and endpoint_fix_5 did not explicitly name
implications in its endpoint. These samples establish the observed endpoint
correction, not universal adherence to every output detail.

- Corrected instruction SHA-256: `d291b48b36f91d45cfb56b6821904cb88b124fcc978fe11beddd5c422fcb261b`
- Affected-case SHA-256: `f1e0c94026a087e1e25ffeb0fa36a414e3315b8c43c3a65408a4dbfe09de9c3b`

| Sample | Actual endpoint excerpt |
|---|---|
| endpoint_fix_1 | “finish the approved intake-and-extraction outcome, verification and review, report evidence, limitations and implications for later capabilities, then stop” |
| endpoint_fix_2 | “deliver the approved intake/extraction outcome, complete verification and review, report evidence, limitations and implications, then stop before later work” |
| endpoint_fix_3 | “deliver working intake and inspectable extraction, complete verification and review, report evidence, limitations and implications for later work, then stop before another increment” |
| endpoint_fix_4 | “complete the approved intake-to-extraction outcome, verification and review, report demonstrated results, accuracy evidence, limitations and implications for later work” |
| endpoint_fix_5 | “complete the approved intake-to-extraction outcome, verification and review, report evidence and limitations, and stop before specifying or implementing later capabilities” |

The original omissions remain recorded above. This brings the behavioral
sample count to nineteen fresh contexts, including targeted correction runs.
No claim of statistical improvement or consistent real-project compliance is
made. The sequential gate resumes at specification review for the corrected
state before quality can begin; this is the same integrated final review seat.


### Final sequential review and handoff

The corrected state passed both stages of the same integrated final seat:

- `SPEC REVIEW: PASS`: complete 14-file boundary matches the approved scope;
  AC-02 correction and its RED/GREEN/targeted evidence accepted; no extra scope.
- `QUALITY REVIEW: PASS`, `Findings: NONE`: no supported quality, security,
  data-integrity or maintainability defect. The reviewer used packaged evidence
  and did not rerun tests.
- Both validated and echoed GATE_RUN_ID
  `9581251e-7919-4b15-b3cf-0967dbc1ea2e`, REVIEWED_STATE_ID
  `86adc6454c8763c0597c70b2f150680d613697da`, and PACKAGE_SHA256
  `5c867bb31b6d6e1580e143d679316f005d2fdbde52ca07a6723f9b71f60caeef`.
  The immutable package hash was checked again before recording these results.
- Latest full verification of the final instruction/test source: exit 0,
  82 repository tests plus 77 plugin tests (159 total), both `OK`, and
  `Repository verification passed.` Final evidence/lifecycle edits do not
  change the instruction/test source or the specification's policy block.
- Rulings: none. Deferred minors: none. The one acceptance miss was corrected
  within the approved scope; no substantive policy or plan change was adopted.

Local commits before this evidence-only handoff are `e090e8d` (approved
artifacts), `406f857` (integration), and `86adc64` (explicit endpoint correction).
The final evidence commit uses `chore: record delivery scope verification`.
Keep branch `chore/delivery-scope` local in the existing checkout. No worktree,
push, merge, dependency installation, cache edit, live profile update, or later
increment was performed.

The result is a repository implementation ready for separately authorized
rollout. After reviewing/selecting the intended revision, use the supported
procedure in [installation](../../installation.md): repository verification;
bootstrap `--check` and `--dry-run`; after explicit authorization, bootstrap
installation; then healthy bootstrap `--check`, installed-skill inspection,
and a new chat to load the instructions. Older guidance can legitimately
report drift before rollout. A profile-only refresh does not refresh skill
content. These instructions document the later action; they do not perform or
authorize it.

Future live use may reveal further wording refinements. The nineteen synthetic
consumers and deterministic distribution checks provide distinct evidence;
they do not prove consistent live agent behavior. Stop here rather than
starting that refinement or rollout scope automatically.
