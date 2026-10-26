import json
import re
import unittest
from copy import deepcopy
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
MARKETPLACE = PLUGIN.parents[1] / ".agents/plugins/marketplace.json"

SUBAGENT_DRIVEN_TASKS = ("task-1", "task-2")
EXPECTED_SUBAGENT_DRIVEN_TRACE = [
    "base:per-task-review:task-1",
    "base:per-task-review:task-2",
    "personal:code-review",
    "base:finishing-a-development-branch",
]


def execution_trace(route, tasks):
    trace = []
    for phase in route["ordered_phases"]:
        if not phase["enabled"]:
            continue
        if phase.get("repeat") == "per-task":
            trace.extend(f"{phase['event']}:{task}" for task in tasks)
        else:
            trace.append(phase["event"])
    return trace


class PluginContractTest(unittest.TestCase):
    def test_delivery_scope_policy_matches_approved_specification(self):
        """A truncated or rewritten distributed policy must fail its copy contract."""
        spec = (PLUGIN.parents[1] / "docs/superpowers/specs/2026-10-26-delivery-scope.md").read_text()
        expected = spec.split("## Delivery scope policy\n", 1)[1].split(
            "## Integration design", 1
        )[0]
        expected = expected[expected.index("- For new projects"):].strip()
        guidance = (PLUGIN / "profile/global-agents-block.md").read_text()
        managed = guidance.split("<!-- personal-workflows:start -->", 1)[1].split(
            "<!-- personal-workflows:end -->", 1
        )[0]
        self.assertEqual(managed.count("## Delivery scope\n"), 1)
        actual = managed.partition("## Delivery scope\n")[2].split("\n## ", 1)[0]
        self.assertEqual(actual.strip(), expected)

    def test_delivery_adapters_expose_increment_boundaries(self):
        """Distribution/link contracts; consumer behavior is evaluated separately."""
        required = {
            "spec-define": ("selected increment", "uncertainty", "deferred work", "boundary rationale", "execution endpoint"),
            "spec-plan": ("approved scope", "execution endpoint", "provisional"),
            "spec-implement": ("working result", "observed evidence", "limitations", "implications", "stop"),
        }
        for name, terms in required.items():
            with self.subTest(adapter=name):
                path = PLUGIN / "skills" / name / "SKILL.md"
                adapter = path.read_text()
                reference = "../../references/delivery-scope.md"
                self.assertIn(reference, adapter)
                self.assertTrue((path.parent / reference).is_file())
                wording = " ".join(adapter.lower().split())
                for term in terms:
                    self.assertIn(term, wording)
                self.assertIn("existing approved", wording)
                if name == "spec-define":
                    self.assertIn("Execution endpoint:", adapter)

    def test_managed_guidance_requires_separate_workflow_approvals(self):
        guidance = (PLUGIN / "profile/global-agents-block.md").read_text()
        start = "<!-- personal-workflows:start -->"
        end = "<!-- personal-workflows:end -->"
        self.assertEqual(guidance.count(start), 1)
        self.assertEqual(guidance.count(end), 1)
        managed = guidance.split(start, 1)[1].split(end, 1)[0]
        headings = (
            "## Personal workflow routing",
            "## Managed model routing",
            "## Working agreements",
            "## Mandatory specification approval workflow",
            "### Stage 1: Scope and design confirmation",
            "### Stage 2: DRAFT specification",
            "### Stage 3: Implementation plan",
            "### Stage 4: Implementation",
            "### Approval interpretation",
            "### Handoffs and mode changes",
            "## Specification and plan naming",
            "## Spec-driven Git workflow",
            "## Interactive clarification",
        )
        previous = -1
        for heading in headings:
            with self.subTest(heading=heading):
                self.assertEqual(managed.splitlines().count(heading), 1)
                position = managed.index(heading)
                self.assertGreater(position, previous)
                previous = position
        wording = " ".join(managed.split())
        for instruction in (
            "Stop and wait for explicit specification approval.",
            "Stop and wait for explicit plan approval.",
            "Specification approval authorizes implementation planning only.",
            "Never combine specification approval and plan approval into one gate.",
            "Leaving Plan mode or accepting a generic implementation prompt does not waive missing gates.",
            "If unavailable, do not draft the artifact.",
            "Clarification answers resolve decisions. They do not replace scope, specification, or implementation-plan approval.",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, wording)
        self.assertTrue(guidance.rstrip().endswith(end))

    def test_managed_fallback_selects_present_superpowers_skill(self):
        guidance = " ".join(
            (PLUGIN / "profile/global-agents-block.md")
            .read_text()
            .lower()
            .split()
        )

        self.assertIn(
            "explicitly select and load the applicable skill from the supplied "
            "`superpowers:*` catalog",
            guidance,
        )
        self.assertIn(
            "when that skill is present in the catalog, do not claim that it is "
            "missing or unavailable",
            guidance,
        )

    def test_marketplace_uses_supported_repository_layout(self):
        self.assertTrue(
            MARKETPLACE.is_file(),
            "marketplace root must contain .agents/plugins/marketplace.json",
        )

    def test_manifest_is_release_ready_and_describes_migrated_workflows(self):
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        interface = manifest["interface"]

        self.assertEqual(manifest["version"], "1.0.0")
        self.assertIn("Superpowers", interface["shortDescription"])
        for field in ("longDescription", "defaultPrompt"):
            wording = interface[field].lower()
            for required in (
                "superpowers",
                "spec-driven",
                "architecture",
                "document",
                "repository-audit",
            ):
                with self.subTest(field=field, required=required):
                    self.assertIn(required, wording)
        ui_copy = " ".join(
            interface[field]
            for field in ("shortDescription", "longDescription", "defaultPrompt")
        ).lower()
        self.assertNotIn("scaffold", ui_copy)

    def test_manifest_and_marketplace_reference_the_same_plugin(self):
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        marketplace = json.loads(MARKETPLACE.read_text())
        self.assertEqual(manifest["name"], "personal-workflows")
        entry = next(item for item in marketplace["plugins"] if item["name"] == manifest["name"])
        self.assertEqual(entry["source"]["path"], "./plugins/personal-workflows")

    def test_integration_map_covers_every_migrated_skill(self):
        mapping = json.loads((PLUGIN / "references/integration-map.json").read_text())
        actual = (
            set(mapping["wrappers"])
            | set(mapping["entry_points"])
            | set(mapping["standalone"])
        )
        expected = {
            "spec-define", "spec-plan", "spec-implement", "implement-lite",
            "code-review", "debug",
            "arch-map", "arch-compare", "arch-design", "doc-ingest",
            "doc-analyze", "doc-estimate", "doc-summarize", "repository-audit",
        }
        self.assertEqual(actual, expected)

    def test_migrated_wrappers_include_skill_and_ui_metadata(self):
        for skill_name in (
            "spec-define", "spec-plan", "spec-implement", "implement-lite", "debug"
        ):
            with self.subTest(skill=skill_name):
                skill = PLUGIN / "skills" / skill_name
                self.assertTrue((skill / "SKILL.md").is_file())
                metadata = skill / "agents/openai.yaml"
                self.assertTrue(metadata.is_file())
                self.assertRegex(
                    metadata.read_text(),
                    r"(?m)^\s*allow_implicit_invocation:\s*true\s*$",
                )

    def test_implementation_wrappers_have_exact_base_dependencies(self):
        mapping = json.loads((PLUGIN / "references/integration-map.json").read_text())

        self.assertEqual(
            mapping["wrappers"]["spec-implement"],
            [
                "using-git-worktrees",
                "executing-plans",
                "subagent-driven-development",
                "test-driven-development",
                "systematic-debugging",
                "verification-before-completion",
                "finishing-a-development-branch",
            ],
        )
        self.assertEqual(mapping["wrappers"]["debug"], ["systematic-debugging"])
        self.assertNotIn("code-review", mapping["wrappers"]["spec-implement"])

    def test_subagent_driven_route_keeps_task_reviews_and_one_personal_final(self):
        mapping = json.loads((PLUGIN / "references/integration-map.json").read_text())
        route = mapping["execution_routes"]["spec-implement"][
            "subagent-driven-development"
        ]
        actual = execution_trace(route, SUBAGENT_DRIVEN_TASKS)

        self.assertEqual(actual, EXPECTED_SUBAGENT_DRIVEN_TRACE)
        self.assertEqual(actual.count("personal:code-review"), 1)
        self.assertFalse(
            any(event.startswith("generic:final-review") for event in actual)
        )

        duplicate_route = deepcopy(route)
        generic_final = next(
            phase
            for phase in duplicate_route["ordered_phases"]
            if phase["event"] == "generic:final-review"
        )
        generic_final["enabled"] = True
        self.assertNotEqual(
            execution_trace(duplicate_route, SUBAGENT_DRIVEN_TASKS),
            EXPECTED_SUBAGENT_DRIVEN_TRACE,
        )

        skill = (PLUGIN / "skills/spec-implement/SKILL.md").read_text()
        normalized = " ".join(skill.lower().split())
        self.assertIn("retain its per-task reviews", normalized)
        self.assertIn("sole final whole-branch review seat", normalized)
        self.assertIn("never dispatch a generic final reviewer", normalized)

    def test_execution_method_precedence_is_deterministic(self):
        mapping = json.loads((PLUGIN / "references/integration-map.json").read_text())
        selection = mapping["execution_routes"]["spec-implement"]["selection"]

        self.assertEqual(
            selection,
            {
                "precedence": [
                    "explicit-current-user-or-handoff",
                    "approved-plan-selection",
                ],
                "conflicting-non-user-sources": "stop-before-loading-either",
            },
        )

    def test_artifact_resolution_requires_paired_names_and_document_dates(self):
        reference = (PLUGIN / "references/artifact-resolution.md").read_text()
        self.assertIn("docs/superpowers/specs/YYYY-MM-DD-<slug>.md", reference)
        self.assertIn("docs/superpowers/plans/YYYY-MM-DD-<slug>.md", reference)
        self.assertNotIn("YYYY-MM-DD-<topic>-design.md", reference)
        for field in ("**Created:**", "**Updated:**", "**Spec:**"):
            with self.subTest(field=field):
                self.assertIn(field, reference)
        normalized = " ".join(reference.split())
        for requirement in (
            r"(?i)specification's original creation date",
            r"(?i)exact basename.*historical suffixes",
            r"(?i)preserve.*Created.*Updated",
            r"(?i)never invent.*historical dates",
            r"(?i)contradictory.*(?:identity|metadata)",
        ):
            with self.subTest(requirement=requirement):
                self.assertRegex(normalized, requirement)

    def test_delivery_adapters_expose_pairing_metadata(self):
        for name in ("spec-define", "spec-plan", "spec-implement"):
            with self.subTest(adapter=name):
                adapter = (PLUGIN / "skills" / name / "SKILL.md").read_text()
                self.assertIn("../../references/artifact-resolution.md", adapter)
                for field in ("**Created:**", "**Updated:**"):
                    self.assertIn(field, adapter)
                if name != "spec-define":
                    self.assertIn("**Spec:**", adapter)

    def test_artifact_resolution_defines_safe_outcomes(self):
        reference_path = PLUGIN / "references/artifact-resolution.md"
        self.assertTrue(reference_path.is_file())
        reference = reference_path.read_text()
        outcomes = {}
        for line in reference.splitlines():
            match = re.fullmatch(
                r"\|\s*(NEW_ONLY|LEGACY_ONLY|SAME_SOURCE|CONFLICT|MISSING)\s*"
                r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
                line,
            )
            if match:
                outcomes[match.group(1)] = {
                    "selected_path": match.group(2).strip(),
                    "behavior": match.group(3).strip(),
                }

        self.assertEqual(
            set(outcomes),
            {"NEW_ONLY", "LEGACY_ONLY", "SAME_SOURCE", "CONFLICT", "MISSING"},
        )
        self.assertEqual(outcomes["CONFLICT"]["selected_path"], "none")
        self.assertRegex(
            outcomes["CONFLICT"]["behavior"],
            r"(?i)request (?:the )?user(?:'s)? selection",
        )


if __name__ == "__main__":
    unittest.main()
