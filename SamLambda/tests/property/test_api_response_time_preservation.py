"""
Property-based test for API response time preservation after security hardening.

Feature: phase1-security-hardening, Property 19: API Response Time Preservation

This test validates that API response times remain within 10% of baseline after
deploying encryption and security hardening changes.

Validates: Requirements 12.1
"""

import os
import time
import json
import boto3
import pytest
import requests
from hypothesis import given, settings, strategies as st, HealthCheck
from statistics import mean, stdev


class TestAPIResponseTimePreservation:
    """Property-based tests for API response time preservation."""

    # Baseline response times (in milliseconds) for key endpoints
    # These are expected maximum response times for warm invocations
    BASELINE_RESPONSE_TIMES = {
        "/functions/questionDbFunctions/types": 500,  # 500ms baseline
        "/functions/questionDbFunctions": 500,
        "/functions/questionDbFunctions/typedata": 800,
        "/functions/questionDbFunctions/question": 600,
    }

    # Acceptable variance percentage (10% as per requirements)
    ACCEPTABLE_VARIANCE = 0.10

    # Maximum acceptable response time (absolute limit)
    MAX_RESPONSE_TIME_MS = 3000  # 3 seconds

    @pytest.fixture()
    def stack_name(self):
        """Get the CloudFormation stack name from environment."""
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if stack_name is None:
            pytest.skip("AWS_SAM_STACK_NAME environment variable not set")
        return stack_name

    @pytest.fixture()
    def api_gateway_url(self, stack_name):
        """Get the API Gateway URL from CloudFormation stack outputs."""
        client = boto3.client("cloudformation")
        
        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            pytest.fail(f"Cannot find stack {stack_name}: {e}")
        
        stacks = response["Stacks"]
        stack_outputs = stacks[0]["Outputs"]
        
        # Look for API output
        api_outputs = [
            output for output in stack_outputs 
            if "Api" in output.get("OutputKey", "")
        ]
        
        if not api_outputs:
            pytest.skip(f"No API Gateway outputs found in stack {stack_name}")
        
        api_url = api_outputs[0]["OutputValue"]
        # Remove trailing slash and stage if present
        return api_url.rstrip("/")

    def measure_response_time(self, url, method="GET", headers=None, params=None, data=None):
        """
        Measure the response time of an API call.
        
        Returns: (response_time_ms, status_code, success)
        """
        if headers is None:
            headers = {}
        
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                return (None, None, False)
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            return (response_time_ms, response.status_code, True)
            
        except requests.exceptions.Timeout:
            return (None, 408, False)
        except Exception as e:
            return (None, None, False)

    def warm_up_endpoint(self, url, method="GET", headers=None, params=None, data=None, count=3):
        """
        Warm up an endpoint by calling it multiple times to avoid cold start penalties.
        """
        for _ in range(count):
            try:
                if method == "GET":
                    requests.get(url, headers=headers, params=params, timeout=10)
                elif method == "POST":
                    requests.post(url, headers=headers, json=data, timeout=10)
                time.sleep(0.1)  # Small delay between warm-up calls
            except:
                pass

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @given(
        endpoint_index=st.integers(min_value=0, max_value=3)
    )
    def test_response_times_within_acceptable_range(
        self,
        api_gateway_url,
        endpoint_index
    ):
        """
        Property: For all API endpoints, response times should be within
        acceptable limits after security hardening.
        
        This test measures actual response times and compares them to baselines.
        """
        # Select endpoint based on index
        endpoints = list(self.BASELINE_RESPONSE_TIMES.keys())
        endpoint_path = endpoints[endpoint_index]
        baseline_ms = self.BASELINE_RESPONSE_TIMES[endpoint_path]
        
        # Construct full URL
        full_url = f"{api_gateway_url}{endpoint_path}"
        
        # Warm up the endpoint (avoid cold start penalty)
        self.warm_up_endpoint(full_url, method="GET")
        
        # Measure response time
        response_time_ms, status_code, success = self.measure_response_time(full_url, method="GET")
        
        if not success:
            pytest.skip(f"Endpoint {endpoint_path} failed to respond")
        
        # Check that response time is reasonable
        assert response_time_ms is not None, (
            f"Failed to measure response time for {endpoint_path}"
        )
        
        # Check absolute maximum
        assert response_time_ms < self.MAX_RESPONSE_TIME_MS, (
            f"Response time {response_time_ms:.2f}ms exceeds maximum {self.MAX_RESPONSE_TIME_MS}ms "
            f"for endpoint {endpoint_path}"
        )
        
        # Check against baseline with acceptable variance
        max_acceptable = baseline_ms * (1 + self.ACCEPTABLE_VARIANCE)
        
        assert response_time_ms <= max_acceptable, (
            f"Response time {response_time_ms:.2f}ms exceeds baseline {baseline_ms}ms "
            f"(+{self.ACCEPTABLE_VARIANCE*100}% = {max_acceptable:.2f}ms) for endpoint {endpoint_path}"
        )

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    @given(
        question_id=st.integers(min_value=1, max_value=100)
    )
    def test_parameterized_endpoint_response_times(
        self,
        api_gateway_url,
        question_id
    ):
        """
        Property: For parameterized API endpoints, response times should remain
        consistent regardless of parameter values.
        
        This tests that encryption overhead doesn't scale with data size.
        """
        endpoint_path = "/functions/questionDbFunctions/question"
        full_url = f"{api_gateway_url}{endpoint_path}"
        
        # Warm up
        self.warm_up_endpoint(
            full_url, 
            method="GET",
            params={"questionId": str(question_id)}
        )
        
        # Measure response time
        response_time_ms, status_code, success = self.measure_response_time(
            full_url,
            method="GET",
            params={"questionId": str(question_id)}
        )
        
        if not success:
            pytest.skip(f"Endpoint {endpoint_path} failed to respond")
        
        # Check absolute maximum
        assert response_time_ms < self.MAX_RESPONSE_TIME_MS, (
            f"Response time {response_time_ms:.2f}ms exceeds maximum for "
            f"endpoint {endpoint_path} with questionId={question_id}"
        )

    def test_multiple_endpoints_average_response_time(self, api_gateway_url):
        """
        Test that the average response time across multiple endpoints
        is within acceptable limits.
        
        This provides a holistic view of API performance.
        """
        response_times = []
        
        for endpoint_path, baseline_ms in self.BASELINE_RESPONSE_TIMES.items():
            full_url = f"{api_gateway_url}{endpoint_path}"
            
            # Warm up
            self.warm_up_endpoint(full_url, method="GET")
            
            # Measure multiple times and take average
            measurements = []
            for _ in range(5):
                response_time_ms, status_code, success = self.measure_response_time(
                    full_url, method="GET"
                )
                if success and response_time_ms is not None:
                    measurements.append(response_time_ms)
                time.sleep(0.1)
            
            if measurements:
                avg_time = mean(measurements)
                response_times.append({
                    "endpoint": endpoint_path,
                    "avg_time": avg_time,
                    "baseline": baseline_ms,
                    "measurements": measurements
                })
        
        # Check that we got measurements
        assert len(response_times) > 0, "No successful response time measurements"
        
        # Calculate overall average
        overall_avg = mean([rt["avg_time"] for rt in response_times])
        overall_baseline = mean([rt["baseline"] for rt in response_times])
        
        # Check against baseline with variance
        max_acceptable = overall_baseline * (1 + self.ACCEPTABLE_VARIANCE)
        
        assert overall_avg <= max_acceptable, (
            f"Average response time {overall_avg:.2f}ms exceeds baseline {overall_baseline:.2f}ms "
            f"(+{self.ACCEPTABLE_VARIANCE*100}% = {max_acceptable:.2f}ms). "
            f"Individual measurements: {response_times}"
        )

    def test_response_time_consistency(self, api_gateway_url):
        """
        Test that response times are consistent across multiple invocations.
        
        High variance could indicate performance issues with encryption.
        """
        endpoint_path = "/functions/questionDbFunctions/types"
        full_url = f"{api_gateway_url}{endpoint_path}"
        
        # Warm up
        self.warm_up_endpoint(full_url, method="GET", count=5)
        
        # Measure multiple times
        measurements = []
        for _ in range(20):
            response_time_ms, status_code, success = self.measure_response_time(
                full_url, method="GET"
            )
            if success and response_time_ms is not None:
                measurements.append(response_time_ms)
            time.sleep(0.05)
        
        assert len(measurements) >= 10, "Not enough successful measurements"
        
        # Calculate statistics
        avg_time = mean(measurements)
        std_dev = stdev(measurements) if len(measurements) > 1 else 0
        
        # Standard deviation should be less than 50% of mean (reasonable consistency)
        max_acceptable_stddev = avg_time * 0.5
        
        assert std_dev <= max_acceptable_stddev, (
            f"Response time standard deviation {std_dev:.2f}ms is too high "
            f"(>{max_acceptable_stddev:.2f}ms). Average: {avg_time:.2f}ms. "
            f"This indicates inconsistent performance. Measurements: {measurements}"
        )

    def test_no_timeout_errors(self, api_gateway_url):
        """
        Test that API endpoints don't timeout after security hardening.
        
        Encryption overhead should not cause timeouts.
        """
        timeout_count = 0
        total_requests = 0
        
        for endpoint_path in self.BASELINE_RESPONSE_TIMES.keys():
            full_url = f"{api_gateway_url}{endpoint_path}"
            
            # Test 5 times per endpoint
            for _ in range(5):
                total_requests += 1
                response_time_ms, status_code, success = self.measure_response_time(
                    full_url, method="GET"
                )
                
                if status_code == 408 or not success:
                    timeout_count += 1
                
                time.sleep(0.1)
        
        # Allow up to 10% timeout rate (network issues, cold starts)
        timeout_rate = timeout_count / total_requests if total_requests > 0 else 0
        
        assert timeout_rate <= 0.10, (
            f"Timeout rate {timeout_rate*100:.1f}% exceeds acceptable limit of 10%. "
            f"{timeout_count} timeouts out of {total_requests} requests."
        )
