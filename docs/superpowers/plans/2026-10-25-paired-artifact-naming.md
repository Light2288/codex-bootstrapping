# Paired Artifact Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make specification/plan pairs easy to identify and resume by sharing a stable basename while preserving historical discovery.

**Architecture:** Update the shared Markdown artifact-resolution contract and its three delivery adapters. Distribute a short naming section through the existing managed guidance block, then separately align the user's global file using a verified backup and atomic replacement. No executable resolver or installer changes are needed.

**Tech Stack:** Markdown workflow instructions, Python 3.11+ unittest, zsh.

**Spec:** [Approved specification](../specs/2026-10-25-paired-artifact-naming.md)

**Slug:** `paired-artifact-naming`
**Created:** 2026-10-25
**Updated:** 2026-10-25
**Provenance:** Approved specification and scope clarification in this chat; native execution retains the user's established inline execution preference.
**Status:** APPROVED
**Approval evidence:** The user approved this separately presented plan with "plan approved".
**Execution method:** Native, through `personal-workflows:spec-implement` and `superpowers:executing-plans`.
**Execution tier:** full
**Implementation model role:** full

The full tier reflects the live-file data risk in Task 2. Native execution retains the current session model.

## Global Constraints and Evidence

- No bulk renaming, reference migration, new installation flag, dependency, or artifact-management command.
- Preserve the current resolution outcomes, conflict safeguards, and legacy read-only behavior.
- Update repository sources and the explicitly authorized global guidance file. Installed plugin caches, Superpowers, credentials, and other live configuration remain outside scope.
- Preserve the separate specification and implementation-plan approval gates and existing Git workflow.
- Work in the existing checkout. Do not create a worktree, push, or merge the implementation branch.
- Repository inspected on `main` at `e995adf54defb4723e24422aa449eb3ffebc2682`. The checkout was clean before saving these artifacts. No architecture map or ADRs are present; none will be generated.
- Both artifact lookups were `MISSING` before these files were saved. Their explicitly requested paths are valid under the current contract. Existing historical artifacts remain untouched.
- Commands below come from `scripts/verify.zsh`: `python3 -m unittest discover -s tests -v`, `python3 -m unittest discover -s plugins/personal-workflows/tests -v`, and `zsh scripts/verify.zsh`. Use a Python 3.11+ interpreter, as required by that script. No tests were rerun during planning.
- The live global file currently equals the packaged template, has exactly one marker pair, and has SHA-256 `01e826bb0c9e337ab164fc0e2954e70d152dbcfebb23bb4fa22fd28b758c1c08`. This is discovery evidence, not permission to overwrite a later edit.

## Review Focus

1. A later planning date must not replace the specification's filename date; test a multi-day pair and subsequent revisions.
2. A historical suffix or differing existing plan name must not cause a rename, duplicate, or failed lookup; test both cases.
3. An explicit path must not silently bypass contradictory identity metadata or new naming requirements; test conflicts and an explicit path without old metadata.
4. Missing historical dates must not become invented `Created` values; test a metadata-poor legacy source and preserve its read-only status.
5. A changed live source, duplicate markers, customized models, or an occupied backup name must not lose user data; exercise the local operation on temporary files first.

### Task 1: Establish the paired artifact contract and distribution [size: M | risk: none | mechanical: true | clear_pattern: true | objectively_verifiable: true | concerns: none]

**Acceptance criteria:** AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-09.

**Files and responsibilities:**

- Modify `plugins/personal-workflows/references/artifact-resolution.md`: authoritative naming, dates, pairing, compatibility, and conflict rules.
- Modify `plugins/personal-workflows/skills/{spec-define,spec-plan,spec-implement}/SKILL.md`: required metadata slots and explicit use of the shared pairing contract at each handoff.
- Modify `plugins/personal-workflows/profile/global-agents-block.md`: concise managed naming guidance before the existing Git workflow, preserving all existing instructions and the marker boundaries.
- Extend `plugins/personal-workflows/tests/test_plugin_contract.py` and `plugins/personal-workflows/tests/test_install_profile.py` using their existing classes and temporary-home helpers.
- Update `docs/workflows.md`, `docs/installation.md`, `README.md`, and the Unreleased section of `CHANGELOG.md` with the convention, compatibility, deployment, and resumption instructions.

**Interfaces:** Keep the five resolution outcomes and current exact-slug/provenance discovery. Plans require shared `Slug`, explicit `Spec`, and document-specific `Created`/`Updated` fields. Continue consuming `install_profile(codex_home: Path, plugin_root: Path, check_only: bool) -> dict` and `merge_managed_block(existing: str, managed: str) -> str`; add no runtime API or CLI.

- [x] **Establish the implementation branch only after plan approval.** Identify this saved plan, the saved approved specification, and their separate approval messages. Inspect local changes, fetch `origin`, and fast-forward `main` safely before creating `chore/paired-artifact-naming`. Preserve these uncommitted artifacts and all other local work; stop on an unsafe update or branch collision without reset, force, or an automatic worktree.

- [x] **Add failing automated contracts.** Add `test_artifact_resolution_requires_paired_names_and_document_dates` and `test_delivery_adapters_expose_pairing_metadata`. Assert that both location patterns use `YYYY-MM-DD-<slug>.md`; the reference requires original-specification-date inheritance, immutable existing basenames, per-document dates, explicit `Spec` references, historical compatibility, and conflict handling. Assert that each delivery adapter links the shared contract and includes the metadata responsibilities appropriate to its stage. Retain `test_artifact_resolution_defines_safe_outcomes` unchanged in purpose. Extend the managed-guidance contract to require exactly one naming section inside the existing marker pair.

  Representative assertions:

  ```python
  self.assertIn("docs/superpowers/specs/YYYY-MM-DD-<slug>.md", reference)
  self.assertIn("docs/superpowers/plans/YYYY-MM-DD-<slug>.md", reference)
  for field in ("**Created:**", "**Updated:**", "**Spec:**"):
      self.assertIn(field, reference)
  self.assertNotIn("YYYY-MM-DD-<topic>-design.md", reference)
  self.assertEqual(managed.count("## Specification and plan naming"), 1)
  ```

- [x] **Exercise installer distribution in a temporary home.** Add `test_naming_guidance_upgrade_preserves_models_and_outside_text`: install an old managed block with custom full/light assignments and unrelated prefix/suffix, verify check mode reports `would-update` without writes, install the new template, and compare the entire result with the rendered expected block. Verify the naming section is inside the markers, the backup equals the original, and check/reinstall report `unchanged` without additional changes or backups. Existing fresh-install, malformed-marker, outside-copy, model-update, and uninstall tests continue to apply.

- [x] **Observe the expected automated failures.** Run `python3 -m unittest discover -s plugins/personal-workflows/tests -v`. Expect the new naming/metadata contract tests to fail against the old guidance. Existing tests must not fail for unrelated reasons.

- [x] **Observe baseline workflow behavior before editing instructions.** Apply `superpowers:writing-skills` and its required background. Use fresh read-only subagent scenarios with no inherited chat history, supplying the current repository adapter/reference text and synthetic fixtures. Ask for resolution, target path, and metadata only; prohibit writes. Preserve actual outputs and failure evidence in the implementation evidence section of this plan. Keep expected answers out of the agents' input and repeat the same scenarios after each relevant adapter change. These are reference-application tests; do not create a production resolver merely to test prose.

  | Adapter/scenario | Fixture and expected result after the change |
  | --- | --- |
  | `spec-define`: new artifact | On 2026-10-25, slug `sample-workflow` produces `specs/2026-10-25-sample-workflow.md` under `docs/superpowers/`, with Created and Updated of 2026-10-25. |
  | `spec-plan`: delayed creation and revision | Specification created 2026-10-25; session 2026-10-28. Plan basename remains `2026-10-25-sample-workflow.md`; its Created/Updated are 2026-10-28. A 2026-10-30 revision changes only Updated and content. |
  | `spec-plan`: historical and legacy sources | A missing plan for `2026-10-24-old-design.md` uses that exact basename. An explicit `specs/old.md` legacy source remains untouched; its new plan uses `docs/superpowers/plans/old.md`, explicit Spec/provenance, and actual plan dates, without inventing a historical spec Created date. |
  | `spec-implement`: later-chat lookup | Slug lookup finds an approved pair with different historical filenames through metadata and explicit Spec. An explicit metadata-poor historical spec path is a valid candidate; matching its plan still requires evidence, not filename guessing. Approval gates still apply. |
  | All relevant adapters: ambiguity | Two same-slug candidates, a Spec/Slug contradiction, contradictory dates on a newly originated pair, or an explicitly requested incompatible new filename require resolution before writing. A request to hurry must not choose the newest candidate or overwrite another file. |

- [x] **Update the shared contract and adapter slots.** Replace the old independent date/name rules with spec-first pairing: resolve the specification and any existing plan before selecting a new plan path. For new specifications, use the creation date and slug; for missing plans, copy the selected specification's basename. Preserve existing names on revisions and preserve all five outcomes, provenance equivalence, and legacy-read/new-write safeguards. Keep slug derivation unchanged. New documents require ISO `YYYY-MM-DD` Created/Updated values; revisions retain known Created and update Updated. Do not backfill unknown historical dates; report missing evidence if a date is necessary. Existing historical naming differences alone are not conflicts. New-path naming conflicts and contradictory identity/date evidence require clarification. Preserve every approval gate.

- [x] **Distribute and document the rules.** Add the single managed naming section with paired paths, stable specification date, per-document dates, Slug/Spec references, and historical exceptions. Documentation includes one delayed-plan example and later-chat prompts such as `Resume paired-artifact-naming` and `Plan from docs/superpowers/specs/2026-10-25-paired-artifact-naming.md`. Explain that packaged guidance reaches installations on update, existing files are not renamed, and the installed plugin cache remains outside this local edit.

- [x] **Verify behavior and repository checks.** Repeat the frozen scenarios using the updated repository instructions, checking each expected outcome and recording actual outputs. Run `python3 -m unittest discover -s plugins/personal-workflows/tests -v`, then `python3 -m unittest discover -s tests -v`, then `zsh scripts/verify.zsh`. Expect exit 0 throughout, all tests passing, and `Repository verification passed.` Inspect the diff to confirm old artifact names/references and installer implementations are unchanged.

- [x] **Commit the verified repository change and approved artifacts.** Commit on the implementation branch with `chore: standardize specification and plan names`. Do not push or merge.

### Task 2: Align the global guidance and finish integrated review [size: S | risk: data | mechanical: true | clear_pattern: true | objectively_verifiable: true | concerns: data]

**Acceptance criteria:** AC-07, AC-08, AC-09.

**Risk:** Replacing live user guidance can lose intervening edits. Verify the source, create the backup exclusively, preserve permissions, and replace atomically.

**Files:** `/Users/davide/.codex/AGENTS.md`, its new sibling backup, and completion evidence in this plan. No other live Codex files.

**Interfaces:** Consume Task 1's verified template and the existing pure merge/model-rendering behavior. Use a one-time local operation, tested outside live state; do not add a migration utility or run the full installer against the user's Codex home.

- [ ] **Prepare the exact transformation without live writes.** Read bytes and file metadata, reject symlinks/non-regular files or malformed/duplicate markers, and inspect changes since planning. Preserve unrelated prefix/suffix and current model selections. Verify the managed content still equals the previous template rendered with those models. If unexpected managed edits exist, preserve them and report the conflict before replacement. Render the new block with the active selections and show the precise prepared diff in the execution evidence.

- [ ] **Exercise the local operation using temporary files.** Cover custom models and unrelated outside content, idempotent preparation, duplicate markers, an existing backup file, a dangling backup symlink, changed source bytes/file identity, and permission preservation. Occupied backup names must remain untouched; intervening source changes must abort without replacing the source. Verify that only the selected target, its backup, and the temporary replacement file are touched. Run the one-time Python rehearsal against `tempfile.TemporaryDirectory`, using assertions for each case; record the invocation and results. This rehearsal is execution evidence, not an added product command.

- [ ] **Back up and replace the authorized global file.** Recheck the source bytes and identity against the inspected version. Create a sibling `AGENTS.md.backup.<n>` using exclusive creation, advancing past all occupied names including symlinks. Store the original bytes and permissions, prepare a same-directory replacement with matching permissions, recheck the source immediately before `os.replace`, and abort if it changed. Do not touch plugin caches or other configuration.

- [ ] **Verify the result and backup.** Read both back: the backup must equal the original bytes and the global file must equal the prepared result. Verify exactly one marker pair and one naming section inside it, unchanged model assignments, unchanged outside content, and preserved permissions. Record the actual backup path and before/after hashes in this plan; do not add the backup to Git.

- [ ] **Complete the final review and corrections.** Invoke `personal-workflows:code-review` once in integrated mode for the required sequential specification and quality reviews of the complete branch. Provide the approved artifacts, full diff, exact commands/results, behavioral scenario evidence, and live-alignment evidence. Handle supported findings through the selected execution workflow, rerunning affected checks after corrections and reconciling the live naming section if those corrections affect it with the same protections.

- [ ] **Finish and report.** Update completion evidence and commit any review corrections/final artifact changes with `chore: record paired artifact naming verification`. Confirm repository status and report commits, tests, scenario results, global alignment, and backup path. Leave the implementation branch local and unmerged.

## Acceptance Traceability

| Criteria | Implementation and proof |
| --- | --- |
| AC-01–AC-03 | Task 1 contract/adapters, metadata assertions, and new/delayed/revision scenarios |
| AC-04–AC-06 | Task 1 metadata/path resumption, historical/legacy cases, and conflict scenarios |
| AC-07 | Task 1 distributed rules/documentation and Task 2 live-file comparison |
| AC-08 | Task 2 temporary rehearsal, source checks, exclusive backup, and read-back comparison |
| AC-09 | Task 1 automated/behavioral verification and Task 2 integrated review |

## Approval Handoff

The user separately approved this plan with "plan approved". Stage 4 implementation is authorized, subject to the recorded Git and live-file protections.


## Implementation Evidence

Separate approvals were observed: the specification was approved in the user message beginning `PLEASE IMPLEMENT THIS PLAN:` that reproduced it; this plan was approved with `plan approved`. Both artifacts were saved before product changes. `origin` was fetched and `main` was already current at `e995adf54defb4723e24422aa449eb3ffebc2682` before creating `chore/paired-artifact-naming` in the existing checkout.

### Workflow consumer scenarios

Two fresh consumers, without inherited chat history, read frozen instruction snapshots and the same ten synthetic fixtures. They returned simulated decisions without writes. These are observed single-run application tests, not a statistical reliability claim. The compact outputs below preserve the actual decisions; date triples refer to filename / Created / Updated.

| Fixture | Baseline output | Updated output |
| --- | --- | --- |
| A: new spec, October 25 | `2026-10-25-sample-workflow-design.md`; no required document dates | `2026-10-25-sample-workflow.md`; Created/Updated `2026-10-25` |
| B: plan October 28, revision October 30 | `2026-10-28-sample-workflow.md`; no required date updates | `2026-10-25-sample-workflow.md`; Created `2026-10-28`, Updated `2026-10-30` after revision; explicit Spec |
| C: missing plan for old spec | `2026-10-28-old.md` | `2026-10-24-old-design.md`; Created/Updated `2026-10-28`; source dates left absent |
| D: selected legacy `specs/old.md` | `MISSING`, asks for slug/topic; filename would use October 28 | `plans/old.md` under `docs/superpowers/`; Slug `old`, Spec/provenance `specs/old.md`, Created/Updated `2026-10-28`; source untouched |
| E: existing mismatched historical names | Selects both existing paths, no rename | Selects both existing paths, no rename |
| F: explicit metadata-poor spec and linked plan | Selects both paths | Selects both paths; linked plan establishes slug `other`; no backfill |
| G: duplicate specs, request to hurry/pick newest | `CONFLICT`, no write | `CONFLICT`, no write |
| H: alpha plan points to beta spec | Proceeds with sole same-slug candidates | `CONFLICT`, no implementation |
| I: new spec filename/Created disagreement | Proceeds, generates October 28 plan | `CONFLICT`, no write |
| J: requested incompatible new filename | Accepts `2026-10-28-special.md` | `CONFLICT`; reports required `2026-10-25-alpha.md` pending resolution |

### Automated verification

- RED: `python3 -m unittest discover -s plugins/personal-workflows/tests -v` exited 1; 74 tests, six expected failures/subtest failures for missing names, metadata, and managed guidance. No unrelated failures.
- GREEN: the same plugin command exited 0; `Ran 74 tests`, `OK`.
- `python3 -m unittest discover -s tests -v` exited 0; `Ran 81 tests`, `OK`.
- `zsh scripts/verify.zsh` exited 0; 81 repository tests, 74 plugin tests, shell/manifests/secret checks, and `Repository verification passed.`
- `git diff --check` passed. Existing historical artifacts, installer implementations, and installed plugin caches were not changed.
