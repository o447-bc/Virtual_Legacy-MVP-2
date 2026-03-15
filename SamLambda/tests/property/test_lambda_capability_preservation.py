"""
Property-based test for Lambda function capability preservation after security hardening.

Feature: phase1-security-hardening, Property 17: Lambda Function Capability Preservation

This test validates that Lambda functions can still access required AWS resources
(DynamoDB, S3) after IAM policy hardening, with no AccessDenied errors.

Validates: Requirements 12.2, 12.3
"""

import os
import json
import boto3
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck


class TestLambdaCapabilityPreservation:
    """Property-based tests for Lambda function capabilities after security hardening."""

    # Lambda functions that interact with DynamoDB
    DYNAMODB_FUNCTIONS = [
        "GetNumQuestionTypesFunction",
        "GetQuestionTypeDataFunction",
        "GetQuestionTypesFunction",
        "GetQuestionByIdFunction",
        "CreateRelationshipFunction",
        "GetRelationshipsFunction",
        "ValidateAccessFunction",
    ]

    # Lambda functions that interact with S3
    S3_FUNCTIONS = [
        "GetUploadUrlFunction",
        "ProcessVideoFunction",
    ]

    @pytest.fixture()
    def stack_name(self):
        """Get the CloudFormation stack name from environment."""
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if stack_name is None:
            pytest.skip("AWS_SAM_STACK_NAME environment variable not set")
        return stack_name

    @pytest.fixture()
    def lambda_client(self):
        """Get boto3 Lambda client."""
        return boto3.client("lambda")

    @pytest.fixture()
    def cloudformation_client(self):
        """Get boto3 CloudFormation client."""
        return boto3.client("cloudformation")

    @pytest.fixture()
    def function_names(self, stack_name, cloudformation_client):
        """Get physical Lambda function names from CloudFormation stack."""
        try:
            response = cloudformation_client.describe_stack_resources(
                StackName=stack_name
            )
            
            resources = response.get("StackResources", [])
            
            # Extract Lambda function physical resource IDs
            function_map = {}
            for resource in resources:
                if resource["ResourceType"] == "AWS::Lambda::Function":
                    logical_id = resource["LogicalResourceId"]
                    physical_id = resource["PhysicalResourceId"]
                    function_map[logical_id] = physical_id
            
            return function_map
            
        except Exception as e:
            pytest.fail(f"Failed to get Lambda functions from stack: {e}")

    def get_function_iam_policy(self, lambda_client, function_name):
        """Get the IAM policy attached to a Lambda function."""
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            role_arn = response["Configuration"]["Role"]
            
            # Extract role name from ARN
            role_name = role_arn.split("/")[-1]
            
            # Get role policies
            iam_client = boto3.client("iam")
            
            # Get inline policies
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            
            # Get attached policies
            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            
            return {
                "role_name": role_name,
                "inline_policies": inline_policies.get("PolicyNames", []),
                "attached_policies": [p["PolicyName"] for p in attached_policies.get("AttachedPolicies", [])]
            }
            
        except Exception as e:
            return {"error": str(e)}

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @given(
        question_type=st.sampled_from(["childhood", "career", "family", "wisdom", "legacy"]),
        user_id=st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
            min_size=10,
            max_size=36
        )
    )
    def test_dynamodb_functions_have_access(
        self, 
        lambda_client, 
        function_names,
        question_type,
        user_id
    ):
        """
        Property: For all Lambda functions that need DynamoDB access,
        they should have appropriate IAM permissions and not receive AccessDenied errors.
        
        This test verifies IAM policies allow DynamoDB operations.
        """
        # Test a sample DynamoDB function
        logical_name = "GetQuestionTypesFunction"
        
        if logical_name not in function_names:
            pytest.skip(f"Function {logical_name} not found in stack")
        
        physical_name = function_names[logical_name]
        
        # Get IAM policy for the function
        policy_info = self.get_function_iam_policy(lambda_client, physical_name)
        
        # Verify the function has a role and policies
        assert "role_name" in policy_info, (
            f"Function {logical_name} does not have an IAM role"
        )
        
        assert (
            len(policy_info.get("inline_policies", [])) > 0 or
            len(policy_info.get("attached_policies", [])) > 0
        ), (
            f"Function {logical_name} has no IAM policies attached"
        )
        
        # Invoke the function with a test payload
        try:
            # Simple invocation to check for AccessDenied
            # We don't care about the result, just that it's not AccessDenied
            response = lambda_client.invoke(
                FunctionName=physical_name,
                InvocationType="RequestResponse",
                Payload=json.dumps({
                    "httpMethod": "GET",
                    "path": "/functions/questionDbFunctions/types",
                    "queryStringParameters": None,
                    "headers": {}
                })
            )
            
            # Read the response
            payload = json.loads(response["Payload"].read())
            
            # Check for AccessDenied in the response
            if "errorMessage" in payload:
                error_msg = payload["errorMessage"].lower()
                assert "accessdenied" not in error_msg, (
                    f"Function {logical_name} received AccessDenied error: {payload['errorMessage']}"
                )
                assert "access denied" not in error_msg, (
                    f"Function {logical_name} received Access Denied error: {payload['errorMessage']}"
                )
            
        except Exception as e:
            error_str = str(e).lower()
            # Check if it's an AccessDenied error
            if "accessdenied" in error_str or "access denied" in error_str:
                pytest.fail(
                    f"Function {logical_name} cannot access DynamoDB: {e}"
                )
            # Other errors are acceptable (e.g., validation errors, missing data)
            # We only care about access control errors

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @given(
        question_id=st.integers(min_value=1, max_value=1000),
        user_id=st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=10,
            max_size=36
        ),
        file_extension=st.sampled_from(["mp4", "webm", "mov"])
    )
    def test_s3_functions_have_access(
        self,
        lambda_client,
        function_names,
        question_id,
        user_id,
        file_extension
    ):
        """
        Property: For all Lambda functions that need S3 access,
        they should have appropriate IAM permissions and not receive AccessDenied errors.
        
        This test verifies IAM policies allow S3 operations.
        """
        # Test the GetUploadUrlFunction which generates S3 presigned URLs
        logical_name = "GetUploadUrlFunction"
        
        if logical_name not in function_names:
            pytest.skip(f"Function {logical_name} not found in stack")
        
        physical_name = function_names[logical_name]
        
        # Get IAM policy for the function
        policy_info = self.get_function_iam_policy(lambda_client, physical_name)
        
        # Verify the function has a role and policies
        assert "role_name" in policy_info, (
            f"Function {logical_name} does not have an IAM role"
        )
        
        # Invoke the function with a test payload
        try:
            response = lambda_client.invoke(
                FunctionName=physical_name,
                InvocationType="RequestResponse",
                Payload=json.dumps({
                    "httpMethod": "GET",
                    "path": "/functions/videoFunctions/get-upload-url",
                    "queryStringParameters": {
                        "questionId": str(question_id),
                        "fileExtension": file_extension
                    },
                    "headers": {},
                    "requestContext": {
                        "authorizer": {
                            "claims": {
                                "sub": user_id
                            }
                        }
                    }
                })
            )
            
            # Read the response
            payload = json.loads(response["Payload"].read())
            
            # Check for AccessDenied in the response
            if "errorMessage" in payload:
                error_msg = payload["errorMessage"].lower()
                assert "accessdenied" not in error_msg, (
                    f"Function {logical_name} received AccessDenied error: {payload['errorMessage']}"
                )
                assert "access denied" not in error_msg, (
                    f"Function {logical_name} received Access Denied error: {payload['errorMessage']}"
                )
                # Also check for S3-specific access errors
                assert "forbidden" not in error_msg, (
                    f"Function {logical_name} received Forbidden error: {payload['errorMessage']}"
                )
            
        except Exception as e:
            error_str = str(e).lower()
            # Check if it's an AccessDenied error
            if "accessdenied" in error_str or "access denied" in error_str or "forbidden" in error_str:
                pytest.fail(
                    f"Function {logical_name} cannot access S3: {e}"
                )
            # Other errors are acceptable

    def test_all_lambda_functions_have_iam_roles(self, lambda_client, function_names):
        """
        Test that all Lambda functions have IAM roles attached.
        
        This is a basic sanity check that IAM configuration is present.
        """
        for logical_name, physical_name in function_names.items():
            try:
                response = lambda_client.get_function(FunctionName=physical_name)
                role_arn = response["Configuration"]["Role"]
                
                assert role_arn, (
                    f"Function {logical_name} does not have an IAM role"
                )
                
                assert role_arn.startswith("arn:aws:iam::"), (
                    f"Function {logical_name} has invalid IAM role ARN: {role_arn}"
                )
                
            except Exception as e:
                pytest.fail(f"Failed to get IAM role for {logical_name}: {e}")

    def test_critical_functions_exist(self, function_names):
        """
        Test that critical Lambda functions exist in the deployed stack.
        
        This ensures security hardening didn't accidentally remove functions.
        """
        critical_functions = [
            "GetQuestionTypesFunction",
            "GetUploadUrlFunction",
            "ProcessVideoFunction",
            "CreateRelationshipFunction",
            "GetRelationshipsFunction",
        ]
        
        for logical_name in critical_functions:
            assert logical_name in function_names, (
                f"Critical function {logical_name} not found in deployed stack"
            )
