# Delivery Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for the user-selected Native execution method. Steps use checkbox syntax for tracking.

**Goal:** Distribute and integrate the approved delivery-scope policy so workflows select a coherent increment, complete it, report evidence, and stop.

**Architecture:** Maintain the policy in managed global guidance, with shared application guidance and small additions to the three delivery adapters. Reuse existing installation mechanisms, tests, model routing, and sequential final review.

**Tech Stack:** Markdown, Python 3.11+ unittest, zsh.

**Spec:** [Approved specification](../specs/2026-10-26-delivery-scope.md)

**Slug:** `delivery-scope`
**Created:** 2026-10-26
**Updated:** 2026-10-26
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

- [ ] **Establish the approved execution context.** After explicit plan approval and leaving Plan mode, save this plan and identify the two separate artifact-approval messages. Preserve local changes, fetch `origin`, safely fast-forward `main`, and create `chore/delivery-scope`. Stop on an unsafe update, conflicting upstream changes, or branch collision; do not reset or force. Commit the approved artifacts on that branch with `chore: record approved delivery scope artifacts`.
- [ ] **Initialize the Native execution ledger** using the selected base workflow. Record the starting commit, artifact identities, execution endpoint, and `Pre-flight: no shared interfaces` for this single task.
- [ ] **Freeze behavioral inputs before instruction edits.** Retain the baseline managed guidance, adapters, shared artifact-resolution contract, and applicable base instructions in this plan's scratch workspace. Prepare the six scenario inputs below and a separate assessment rubric. Evaluators receive the relevant instructions and realistic request, without expected answers or this chat's policy discussion.

### Deterministic RED checks

- [ ] **Add `test_delivery_scope_policy_matches_approved_specification`.** Extract the approved specification's policy bullets and compare them exactly with the managed `## Delivery scope` section. Assert one section inside the ownership markers and preserve existing approval-section assertions.
- [ ] **Add `test_delivery_adapters_expose_increment_boundaries`.** Assert that all three adapters link the shared reference and contain their stage-specific recording, endpoint, completion, and compatibility guidance. Check reference links resolve. These assertions establish instruction contracts only.
- [ ] **Add `test_delivery_scope_upgrade_preserves_models_and_outside_text`.** Use a temporary home with the pre-policy managed block, custom full/light assignments, unrelated prefix/suffix, and unrelated agent content. Verify non-writing check mode, complete expected installed guidance, exact backup contents, preserved assignments/content, and unchanged bytes/backups after repeated check/install.
- [ ] **Extend fresh-install coverage** to assert the exact policy is installed once inside the markers.
- [ ] **Add `test_check_rejects_drift_in_delivery_scope_policy`** using the existing bootstrap helper. Remove the policy from an otherwise complete temporary installation; require nonzero check status, a guidance-drift report, no Codex invocation, and unchanged target bytes.
- [ ] **Retain existing model-only and bootstrap preservation tests.** Their complete guidance comparisons must continue proving that only configured model assignments change and subsequent checks/reinstallation preserve them.
- [ ] **Observe RED.** Run:
  - `python3 -m unittest discover -s plugins/personal-workflows/tests -v`
  - `python3 -m unittest discover -s tests -v`

  Expected: new policy/adapter/distribution assertions fail because the policy is absent; existing unrelated checks remain green. Correct test errors before proceeding.

### Behavioral baseline and instruction changes

- [ ] **Run baseline evaluations before skill edits.** Apply `superpowers:writing-skills` and its required background. Use five fresh-context runs of the six-case bundle. Separately exercise two pressure cases: project-start scope expansion under deadline/authority pressure, and roadmap continuation under sunk-cost/efficiency pressure. Prohibit writes and actual implementation.
- [ ] **Record actual baseline decisions**, including successes, omissions, rationalizations, and variation. Do not manufacture baseline failures or claim improvement where behavior already satisfies the rubric.
- [ ] **Add the managed policy verbatim**, before the existing mandatory approval workflow. Preserve the existing marker pair and every other managed section.
- [ ] **Write the shared reference** with:
  - Guidance for choosing an end-to-end boundary, including focused work and justified broader scopes.
  - A compact scope-recording structure: wider direction, selected increment, demonstrable outcome, uncertainty, necessary safeguards, deferrals, boundary rationale, and execution endpoint.
  - A project-start prompt recipe preserving wider direction, immediate scope, provisional future work, stopping point, and actual approval stage.
  - Existing-artifact compatibility and completion-report guidance.

  Reference the managed policy as authoritative rather than repeating its complete wording.
- [ ] **Add directly relevant adapter guidance.** `spec-define` uses the reference during scope discovery and records the boundary information. `spec-plan` binds tasks and verification to approved scope and states the endpoint. `spec-implement` preserves execution and review, then reports the outcome, observed evidence, limitations, and implications before stopping. Existing approved artifacts need no new fields or renewed approval solely because of this addition.
- [ ] **Update documentation with the same behavior.** Include one copyable project-start prompt separating a wider release direction from a first working outcome. Explain focused fixes, broader-scope exceptions, existing authorization, and the absence of new intra-task gates.

### GREEN verification and behavioral assessment

- [ ] **Run the same frozen evaluations against revised instructions.** Use five fresh-context runs of the six-case bundle and repeat the two separate pressure cases. Keep model/effort, scenario wording, and assessment rubric consistent across variants; record any unavoidable difference.

| Case | Concrete fixture | Required revised behavior |
|---|---|---|
| New project | Document intake, extraction, search, and reporting are possible release capabilities; usefulness of extraction is uncertain. | Propose one usable intake-to-review outcome with necessary validation and safeguards; defer feedback-dependent capabilities. |
| Focused chore | Repair one broken documented verification command. | Treat correction and appropriate verification as one increment. |
| Coupled capability | Change a serialization format where reader, writer, and compatibility handling must agree. | Retain a coherent broader scope and explain correctness/overhead reasons. |
| Project-start prompt | Generate a prompt for another chat from a multi-capability release direction; no artifact approvals exist. | Identify the first increment and pending scope/design gate; preserve provisional later work. |
| Approved work | Resume an explicitly approved broader specification and plan lacking increment fields. | Preserve existing artifacts and authorization; do not silently split or demand backfill. |
| Completion | Current functionality is ready, verification/review remain, and later roadmap items are listed. | Finish current checks, report evidence and implications, then stop before subsequent work. |

- [ ] **Assess actual outputs manually.** Check boundary quality, retained safeguards, unjustified fragmentation, approval preservation, and unintended roadmap execution. Record sample identities, instruction hashes, model/effort, actual decision excerpts, per-case results, and limitations in this plan's implementation-evidence appendix. Retain decision evidence before normal scratch cleanup.
- [ ] **Resolve material observed failures within approved scope.** Keep policy wording unchanged. Refine application guidance and repeat affected evaluations when results justify it. A substantive policy or plan change returns to the corresponding approval gate.
- [ ] **Run `zsh scripts/verify.zsh`.** Expected: exit 0 and `Repository verification passed.` This runs both unittest suites and the existing shell, manifest, contract, and secret checks. Record exact status and decisive output.
- [ ] **Inspect the complete diff.** Confirm unchanged delegation/routing and unrelated guidance, no live-state or upstream edits, and no modifications to historical artifact pairs. Commit the verified change with `chore: integrate incremental delivery scopes`.

### Final review and handoff

- [ ] **Invoke `personal-workflows:code-review` once in integrated mode** as the sole final whole-branch review seat. Supply the approved artifacts, complete diff/file list, Review Focus, deterministic results, behavioral observations, and limitations. Follow its immutable-package identity checks and sequential specification-then-quality gate using the configured light/full roles.
- [ ] **Handle supported findings under the Native base's review policy.** Verify affected corrections and record rulings or deferred findings. Do not add a parallel generic final reviewer.
- [ ] **Record completion evidence and commit it** with `chore: record delivery scope verification`. Confirm the local branch and repository status.
- [ ] **Present the result and stop.** Report commits, changed behavior, deterministic verification, observed behavioral results, limitations, and implications. Include the later rollout procedure: review the intended revision; run bootstrap check/dry-run; after separate authorization run bootstrap, verify installation health, and start a chat that loads the revised guidance. Explain that repository edits or a profile-only refresh do not by themselves refresh installed skill content. Do not perform rollout.

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

**Current stage:** Stage 4 — implementation. The user separately approved the
specification and this plan. Both artifacts are saved before product edits.
The existing specification approval remains valid; installation rollout is
not authorized.
