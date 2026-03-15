"""
Integration test for API endpoint preservation after security hardening.

Feature: phase1-security-hardening, Property 16: API Endpoint Preservation

This test validates that all existing API endpoints and methods remain unchanged
after deploying security hardening changes.

Validates: Requirements 12.4
"""

import os
import boto3
import pytest


class TestAPIEndpointPreservation:
    """Test that API Gateway endpoints are preserved after security changes."""

    # Expected API endpoints based on template.yml
    # Format: (path, method, function_name)
    EXPECTED_ENDPOINTS = [
        # Question DB Functions
        ("/functions/questionDbFunctions", "GET", "GetNumQuestionTypesFunction"),
        ("/functions/questionDbFunctions/typedata", "GET", "GetQuestionTypeDataFunction"),
        ("/functions/questionDbFunctions/get-audio-summary-for-video", "GET", "GetAudioQuestionSummaryForVideoRecordingFunction"),
        ("/functions/questionDbFunctions/get-audio-summary-for-video", "OPTIONS", "GetAudioQuestionSummaryForVideoRecordingFunction"),
        ("/functions/questionDbFunctions/validcount", "GET", "GetNumValidQuestionsForQTypeFunction"),
        ("/functions/questionDbFunctions/totalvalidcount", "GET", "GetTotalValidAllQuestionsFunction"),
        ("/functions/questionDbFunctions/totalvalidcount", "OPTIONS", "GetTotalValidAllQuestionsFunction"),
        ("/functions/questionDbFunctions/invalidate-total-cache", "POST", "InvalidateTotalValidQuestionsCacheFunction"),
        ("/functions/questionDbFunctions/invalidate-total-cache", "OPTIONS", "InvalidateTotalValidQuestionsCacheFunction"),
        ("/functions/questionDbFunctions/usercompletedcount", "GET", "GetUserCompletedQuestionCountFunction"),
        ("/functions/questionDbFunctions/usercompletedcount", "OPTIONS", "GetUserCompletedQuestionCountFunction"),
        ("/functions/questionDbFunctions/types", "GET", "GetQuestionTypesFunction"),
        ("/functions/questionDbFunctions/unanswered", "GET", "GetUnansweredQuestionsFromUserFunction"),
        ("/functions/questionDbFunctions/unanswered", "OPTIONS", "GetUnansweredQuestionsFromUserFunction"),
        ("/functions/questionDbFunctions/question", "GET", "GetQuestionByIdFunction"),
        ("/functions/questionDbFunctions/unansweredwithtext", "GET", "GetUnansweredQuestionsWithTextFunction"),
        ("/functions/questionDbFunctions/unansweredwithtext", "OPTIONS", "GetUnansweredQuestionsWithTextFunction"),
        ("/functions/questionDbFunctions/progress-summary", "GET", "GetProgressSummaryFunction"),
        ("/functions/questionDbFunctions/progress-summary", "OPTIONS", "GetProgressSummaryFunction"),
        ("/functions/questionDbFunctions/progress-summary-2", "GET", "GetProgressSummary2Function"),
        ("/functions/questionDbFunctions/progress-summary-2", "OPTIONS", "GetProgressSummary2Function"),
        
        # Relationship Functions
        ("/relationships", "POST", "CreateRelationshipFunction"),
        ("/relationships", "GET", "GetRelationshipsFunction"),
        ("/relationships/validate", "POST", "ValidateAccessFunction"),
        
        # Video Functions
        ("/functions/videoFunctions/get-upload-url", "GET", "GetUploadUrlFunction"),
        ("/functions/videoFunctions/get-upload-url", "OPTIONS", "GetUploadUrlFunction"),
        ("/functions/videoFunctions/process-video", "POST", "ProcessVideoFunction"),
        ("/functions/videoFunctions/process-video", "OPTIONS", "ProcessVideoFunction"),
    ]

    @pytest.fixture()
    def stack_name(self):
        """Get the CloudFormation stack name from environment."""
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if stack_name is None:
            pytest.skip("AWS_SAM_STACK_NAME environment variable not set")
        return stack_name

    @pytest.fixture()
    def api_gateway_id(self, stack_name):
        """Get the API Gateway REST API ID from CloudFormation stack."""
        client = boto3.client("cloudformation")
        
        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            pytest.fail(f"Cannot find stack {stack_name}: {e}")
        
        stacks = response["Stacks"]
        if not stacks:
            pytest.fail(f"Stack {stack_name} not found")
        
        # Look for ServerlessRestApi output
        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [
            output for output in stack_outputs 
            if "Api" in output.get("OutputKey", "")
        ]
        
        if not api_outputs:
            pytest.fail(f"No API Gateway outputs found in stack {stack_name}")
        
        # Extract API ID from the API Gateway URL
        # Format: https://{api-id}.execute-api.{region}.amazonaws.com/{stage}
        api_url = api_outputs[0]["OutputValue"]
        api_id = api_url.split("//")[1].split(".")[0]
        
        return api_id

    @pytest.fixture()
    def api_resources(self, api_gateway_id):
        """Get all API Gateway resources and methods."""
        client = boto3.client("apigateway")
        
        try:
            # Get all resources
            resources_response = client.get_resources(
                restApiId=api_gateway_id,
                limit=500  # Maximum allowed
            )
            
            resources = resources_response.get("items", [])
            
            # Build list of (path, method) tuples
            endpoints = []
            for resource in resources:
                path = resource.get("path", "")
                resource_methods = resource.get("resourceMethods", {})
                
                for method in resource_methods.keys():
                    if method != "ANY":  # Skip ANY methods
                        endpoints.append((path, method))
            
            return endpoints
            
        except Exception as e:
            pytest.fail(f"Failed to get API Gateway resources: {e}")

    def test_all_expected_endpoints_exist(self, api_resources):
        """
        Test that all expected API endpoints exist in the deployed API Gateway.
        
        This validates that security hardening did not remove any endpoints.
        """
        # Extract just path and method from expected endpoints
        expected_paths_methods = {
            (path, method) 
            for path, method, _ in self.EXPECTED_ENDPOINTS
        }
        
        # Convert actual resources to set
        actual_paths_methods = set(api_resources)
        
        # Check that all expected endpoints exist
        missing_endpoints = expected_paths_methods - actual_paths_methods
        
        assert not missing_endpoints, (
            f"Missing API endpoints after security hardening: {missing_endpoints}"
        )

    def test_no_unexpected_endpoints_added(self, api_resources):
        """
        Test that no unexpected endpoints were added during security hardening.
        
        This ensures the API surface area hasn't expanded unexpectedly.
        """
        # Extract just path and method from expected endpoints
        expected_paths_methods = {
            (path, method) 
            for path, method, _ in self.EXPECTED_ENDPOINTS
        }
        
        # Convert actual resources to set
        actual_paths_methods = set(api_resources)
        
        # Filter out root path and common AWS paths
        filtered_actual = {
            (path, method) 
            for path, method in actual_paths_methods 
            if path != "/" and not path.startswith("/{proxy+}")
        }
        
        # Check for unexpected endpoints
        unexpected_endpoints = filtered_actual - expected_paths_methods
        
        # Allow for some flexibility with OPTIONS methods (CORS)
        unexpected_non_options = {
            (path, method) 
            for path, method in unexpected_endpoints 
            if method != "OPTIONS"
        }
        
        assert not unexpected_non_options, (
            f"Unexpected API endpoints found: {unexpected_non_options}"
        )

    def test_endpoint_count_matches(self, api_resources):
        """
        Test that the total number of endpoints matches expectations.
        
        This is a sanity check to catch bulk changes.
        """
        # Filter out root and proxy paths
        filtered_actual = [
            (path, method) 
            for path, method in api_resources 
            if path != "/" and not path.startswith("/{proxy+}")
        ]
        
        expected_count = len(self.EXPECTED_ENDPOINTS)
        actual_count = len(filtered_actual)
        
        # Allow for some variance due to OPTIONS methods
        variance_threshold = 10  # Allow up to 10 extra OPTIONS endpoints
        
        assert abs(actual_count - expected_count) <= variance_threshold, (
            f"Endpoint count mismatch: expected ~{expected_count}, got {actual_count}. "
            f"Difference: {actual_count - expected_count}"
        )
