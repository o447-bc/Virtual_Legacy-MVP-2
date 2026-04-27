"""
Tests to validate that template.yml contains the required environment variable
and IAM policy for the theme-aware AI prompts feature.

Validates: Requirements 6.1, 6.2
"""
import os
import yaml
import pytest

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "template.yml"
)


@pytest.fixture(scope="module")
def template():
    with open(TEMPLATE_PATH, "r") as f:
        # Use yaml.safe_load — SAM intrinsic functions (!Sub, !Ref, etc.)
        # are loaded as tagged objects; we handle them with a custom loader.
        loader = yaml.SafeLoader
        # Register constructors for common CloudFormation intrinsic functions
        for tag in ("!Sub", "!Ref", "!GetAtt", "!Join", "!Select", "!If", "!Not", "!Equals"):
            loader.add_constructor(
                tag,
                lambda loader, node: loader.construct_scalar(node)
                if isinstance(node, yaml.ScalarNode)
                else loader.construct_sequence(node),
            )
        f.seek(0)
        return yaml.load(f, Loader=loader)


def _get_ws_default_function(template):
    return template["Resources"]["WebSocketDefaultFunction"]["Properties"]


class TestTableAllQuestionsEnvVar:
    """Task 1.1: TABLE_ALL_QUESTIONS env var must be present."""

    def test_env_var_exists(self, template):
        props = _get_ws_default_function(template)
        env_vars = props["Environment"]["Variables"]
        assert "TABLE_ALL_QUESTIONS" in env_vars, (
            "TABLE_ALL_QUESTIONS env var missing from WebSocketDefaultFunction"
        )

    def test_env_var_value(self, template):
        props = _get_ws_default_function(template)
        env_vars = props["Environment"]["Variables"]
        assert env_vars["TABLE_ALL_QUESTIONS"] == "allQuestionDB", (
            "TABLE_ALL_QUESTIONS should be set to 'allQuestionDB'"
        )


class TestDynamoDBGetItemPolicy:
    """Task 1.2: dynamodb:GetItem on allQuestionDB must be in Policies."""

    def test_getitem_policy_exists(self, template):
        props = _get_ws_default_function(template)
        policies = props["Policies"]

        found = False
        for policy in policies:
            if not isinstance(policy, dict):
                continue
            statements = policy.get("Statement", [])
            if not isinstance(statements, list):
                continue
            for stmt in statements:
                if not isinstance(stmt, dict):
                    continue
                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                resources = stmt.get("Resource", [])
                if isinstance(resources, str):
                    resources = [resources]

                has_getitem = "dynamodb:GetItem" in actions
                has_allquestion_resource = any(
                    "allQuestionDB" in str(r) for r in resources
                )
                if has_getitem and has_allquestion_resource:
                    found = True
                    break
            if found:
                break

        assert found, (
            "No IAM policy statement granting dynamodb:GetItem on allQuestionDB "
            "found in WebSocketDefaultFunction Policies"
        )

    def test_policy_effect_is_allow(self, template):
        props = _get_ws_default_function(template)
        policies = props["Policies"]

        for policy in policies:
            if not isinstance(policy, dict):
                continue
            statements = policy.get("Statement", [])
            if not isinstance(statements, list):
                continue
            for stmt in statements:
                if not isinstance(stmt, dict):
                    continue
                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                resources = stmt.get("Resource", [])
                if isinstance(resources, str):
                    resources = [resources]

                has_getitem = "dynamodb:GetItem" in actions
                has_allquestion_resource = any(
                    "allQuestionDB" in str(r) for r in resources
                )
                if has_getitem and has_allquestion_resource:
                    assert stmt.get("Effect") == "Allow", (
                        "dynamodb:GetItem policy on allQuestionDB should have Effect: Allow"
                    )
                    return

        pytest.fail("Policy statement not found — cannot verify Effect")
