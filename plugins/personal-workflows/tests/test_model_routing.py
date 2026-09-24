import json
import re
import tomllib
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
INTEGRATION_MAP = PLUGIN / "references" / "integration-map.json"
TASK_METADATA = re.compile(
    r"^### Task \d+: .+ "
    r"\[size: (?P<size>S|M|L) \| "
    r"risk: (?P<risk>none|security|data|concurrency|migrations|other) \| "
    r"mechanical: (?P<mechanical>true|false) \| "
    r"clear_pattern: (?P<clear_pattern>true|false) \| "
    r"objectively_verifiable: (?P<objectively_verifiable>true|false) \| "
    r"concerns: (?P<concerns>none|[a-z_, -]+)\]$",
    flags=re.MULTILINE,
)


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
        and not task["concerns"]
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


def parse_plan_case(path):
    contents = path.read_text(encoding="utf-8")
    tier_match = re.search(r"^\*\*Execution tier:\*\* (lite|full)$", contents, re.MULTILINE)
    tasks = []
    for match in TASK_METADATA.finditer(contents):
        task = match.groupdict()
        for field in ("mechanical", "clear_pattern", "objectively_verifiable"):
            task[field] = task[field] == "true"
        task["concerns"] = (
            []
            if task["concerns"] == "none"
            else [item.strip() for item in task["concerns"].split(",")]
        )
        tasks.append(task)
    if tier_match is None or not tasks:
        raise AssertionError("fixture is not a realistic routed plan artifact")
    return {
        "requested_tier": tier_match.group(1),
        "execution_method": "subagent-driven-development",
        "tasks": tasks,
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
        self.assertEqual(
            plan_contract["required_task_routing_fields"],
            [
                "size",
                "risk",
                "mechanical",
                "clear_pattern",
                "objectively_verifiable",
                "concerns",
            ],
        )

    def test_realistic_plan_artifact_routes_from_persisted_eligibility_fields(self):
        """Dropping task eligibility fields from plans makes lite routing inferential."""
        mapping = self.load_mapping()
        contract = mapping["model_routing"]
        case = parse_plan_case(FIXTURES / "eligible-lite-plan.md")

        self.assertEqual(
            mapping["planning"]["spec-plan"]["required_task_routing_fields"],
            contract["lite_eligibility"]["required_task_fields"],
        )
        self.assertEqual(
            resolve_case(contract, case),
            {
                "tier": "lite",
                "implementation_model": "gpt-5.6-luna",
                "limitation": None,
            },
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
        for field in plan_contract["required_task_routing_fields"]:
            with self.subTest(task_field=field):
                self.assertIn(f"{field}:", plan_skill)
                self.assertIn(f"{field}:", implement_skill)
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

    def test_final_review_models_follow_configurable_roles_with_exact_defaults(self):
        """Pinning reviewer names to literals would discard supported model overrides."""
        contract = self.load_mapping()["model_routing"]
        roles = {
            "review-spec": "light",
            "review-quality": "full",
        }

        self.assertEqual(contract["final_review_model_roles"], roles)
        defaults = {
            agent: contract["managed_models"][role] for agent, role in roles.items()
        }
        self.assertEqual(
            defaults,
            {
                "review-spec": "gpt-5.6-luna",
                "review-quality": "gpt-5.6-sol",
            },
        )
        custom_models = {"light": "supported-light", "full": "supported-full"}
        self.assertEqual(
            {agent: custom_models[role] for agent, role in roles.items()},
            {
                "review-spec": "supported-light",
                "review-quality": "supported-full",
            },
        )
        for agent, model in defaults.items():
            with self.subTest(agent=agent):
                profile = tomllib.loads(
                    (PLUGIN / "codex-agents" / f"{agent}.toml").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(profile["model"], model)


if __name__ == "__main__":
    unittest.main()
