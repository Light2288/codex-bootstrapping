import json
import re
import tomllib
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
INTEGRATION_MAP = PLUGIN / "references" / "integration-map.json"


def task_is_lite_eligible(task, eligibility):
    required = eligibility["required_task_fields"]
    if any(field not in task for field in required):
        return False
    return (
        task["size"] in eligibility["allowed_sizes"]
        and task["risk"] == eligibility["required_risk"]
        and task["mechanical"]
        and task["clear_pattern"]
        and task["objectively_verifiable"]
    )


def resolve_case(contract, case):
    selected_tier = case["requested_tier"]
    has_full_only_concern = any(
        set(task.get("concerns", [])) & set(contract["full_only_concerns"])
        for task in case["tasks"]
    )
    if selected_tier == "lite" and (
        has_full_only_concern
        or not all(
            task_is_lite_eligible(task, contract["lite_eligibility"])
            for task in case["tasks"]
        )
    ):
        selected_tier = contract["escalation_tier"]

    execution = contract["execution_methods"][case["execution_method"]]
    implementation_model = None
    if execution["can_set_subagent_model"]:
        model_role = contract["tiers"][selected_tier]["implementation_model_role"]
        implementation_model = contract["managed_models"][model_role]

    return {
        "tier": selected_tier,
        "implementation_model": implementation_model,
        "limitation": execution.get("limitation"),
    }


class ModelRoutingContractTest(unittest.TestCase):
    def load_mapping(self):
        return json.loads(INTEGRATION_MAP.read_text(encoding="utf-8"))

    def test_model_routing_scenarios_are_deterministic(self):
        contract = self.load_mapping()["model_routing"]
        cases = json.loads(
            (FIXTURES / "model-routing-cases.json").read_text(encoding="utf-8")
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                actual = resolve_case(contract, case)
                self.assertEqual(actual["tier"], case["expected_tier"])
                self.assertEqual(
                    actual["implementation_model"],
                    case["expected_implementation_model"],
                )
                self.assertEqual(
                    actual["limitation"], case.get("expected_limitation")
                )

    def test_execution_capabilities_are_explicitly_child_scoped(self):
        methods = self.load_mapping()["model_routing"]["execution_methods"]

        self.assertEqual(
            methods["subagent-driven-development"],
            {"can_set_subagent_model": True},
        )
        self.assertEqual(
            methods["executing-plans"],
            {
                "can_set_subagent_model": False,
                "limitation": "cannot-switch-parent-model",
            },
        )
        self.assertNotIn("can_override_parent_model", str(methods))

    def test_implement_lite_is_a_thin_single_delegate_entry_point(self):
        mapping = self.load_mapping()
        contract = mapping["entry_points"]["implement-lite"]
        skill_path = PLUGIN / "skills" / "implement-lite" / "SKILL.md"
        metadata_path = skill_path.parent / "agents" / "openai.yaml"

        self.assertEqual(
            contract,
            {
                "delegate": "spec-implement",
                "load": "exactly-once",
                "requested_tier": "lite",
            },
        )
        self.assertTrue(skill_path.is_file())
        self.assertTrue(metadata_path.is_file())
        body = skill_path.read_text(encoding="utf-8")
        self.assertEqual(body.count("`$spec-implement`"), 1)
        for duplicated_base in (
            "superpowers:using-git-worktrees",
            "superpowers:executing-plans",
            "superpowers:subagent-driven-development",
            "superpowers:test-driven-development",
            "superpowers:verification-before-completion",
            "superpowers:finishing-a-development-branch",
        ):
            with self.subTest(base=duplicated_base):
                self.assertNotIn(duplicated_base, body)

    def test_plan_contract_records_tier_and_model_role(self):
        plan_contract = self.load_mapping()["planning"]["spec-plan"]

        self.assertEqual(
            plan_contract["required_routing_metadata"],
            ["execution_tier", "implementation_model_role"],
        )
        self.assertEqual(
            plan_contract["tier_to_model_role"],
            {"lite": "light", "full": "full"},
        )

    def test_skill_documents_apply_the_machine_readable_routing_contract(self):
        mapping = self.load_mapping()
        plan_contract = mapping["planning"]["spec-plan"]
        routing = mapping["model_routing"]
        plan_skill = " ".join(
            (PLUGIN / "skills" / "spec-plan" / "SKILL.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        implement_skill = " ".join(
            (PLUGIN / "skills" / "spec-implement" / "SKILL.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )

        for tier, role in plan_contract["tier_to_model_role"].items():
            with self.subTest(tier=tier):
                self.assertIn(f"`**execution tier:** {tier}`", plan_skill)
                self.assertIn(
                    f"`**implementation model role:** {role}`", plan_skill
                )
        for role, model in routing["managed_models"].items():
            with self.subTest(role=role):
                self.assertIn(f"`{role}` = `{model}`", implement_skill)
        for concern in routing["full_only_concerns"]:
            with self.subTest(concern=concern):
                self.assertIn(f"`{concern}`", implement_skill)
        self.assertIn(
            "every eligible `lite` implementer dispatch must explicitly set "
            "the resolved `light` model",
            implement_skill,
        )
        self.assertIn(
            "every `full` dispatch and every escalated or replacement "
            "implementer dispatch must explicitly set the resolved `full` model",
            implement_skill,
        )
        self.assertIn(
            "inline execution cannot switch the current parent model",
            implement_skill,
        )

    def test_managed_guidance_publishes_the_contract_model_names(self):
        contract = self.load_mapping()["model_routing"]
        guidance = (PLUGIN / "profile" / "global-agents-block.md").read_text(
            encoding="utf-8"
        )
        published = dict(
            re.findall(
                r"^- `(full|light)`: `([^`]+)`$", guidance, flags=re.MULTILINE
            )
        )

        self.assertEqual(published, contract["managed_models"])

    def test_final_review_keeps_quality_on_sol_and_spec_on_luna(self):
        contract = self.load_mapping()["model_routing"]
        expected = {
            "review-spec": "gpt-5.6-luna",
            "review-quality": "gpt-5.6-sol",
        }

        self.assertEqual(contract["final_review_models"], expected)
        for agent, model in expected.items():
            with self.subTest(agent=agent):
                profile = tomllib.loads(
                    (PLUGIN / "codex-agents" / f"{agent}.toml").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(profile["model"], model)


if __name__ == "__main__":
    unittest.main()
