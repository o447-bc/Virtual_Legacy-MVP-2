#!/usr/bin/env python3
"""
Virtual Legacy Invite System End-to-End Test Suite

This comprehensive test suite validates the complete invite functionality
without requiring the UI. It tests:
1. API endpoint accessibility and authentication
2. Lambda function execution and response format
3. SES email sending integration
4. Error handling and edge cases
5. Performance and reliability metrics

Author: Virtual Legacy Development Team
Date: 2024
"""

import boto3
import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

class Colors:
    """ANSI color codes for terminal output formatting"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class InviteSystemTester:
    """
    Comprehensive test suite for the Virtual Legacy invite system.
    
    This class performs end-to-end testing of the invite functionality,
    including API calls, authentication, email delivery, and error handling.
    """
    
    def __init__(self):
        """
        Initialize the test suite with configuration and test data.
        
        Sets up API endpoints, test email addresses, and AWS clients
        for comprehensive testing of the invite system.
        """
        print(f"{Colors.BOLD}{Colors.BLUE}🚀 Initializing Virtual Legacy Invite System Test Suite{Colors.END}")
        print(f"{Colors.CYAN}=" * 70 + Colors.END)
        
        # API Configuration - matches the deployed SAM application
        self.api_base_url = "https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod"
        self.invite_endpoint = f"{self.api_base_url}/invites/send"
        
        # Test email addresses (must be verified in SES sandbox)
        self.test_emails = ["legacymaker1@o447.net", "legacymaker2@o447.net"]
        
        # This would need to be a verified sender email in your SES
        # For testing, you'll need to replace with your verified email
        self.benefactor_email = "legacyBenefactor1@o447.net"  # Replace with verified email
        
        # Test configuration
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "start_time": datetime.now(),
            "test_details": []
        }
        
        # AWS clients for direct service testing
        try:
            self.ses_client = boto3.client('ses', region_name='us-east-1')
            self.lambda_client = boto3.client('lambda', region_name='us-east-1')
            print(f"{Colors.GREEN}✓ AWS clients initialized successfully{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to initialize AWS clients: {str(e)}{Colors.END}")
            print(f"{Colors.YELLOW}⚠ Make sure AWS credentials are configured{Colors.END}")
        
        print(f"{Colors.CYAN}Configuration loaded:{Colors.END}")
        print(f"  • API Endpoint: {self.invite_endpoint}")
        print(f"  • Test Emails: {', '.join(self.test_emails)}")
        print(f"  • Benefactor Email: {self.benefactor_email}")
        print()

    def log_test_result(self, test_name: str, status: str, details: str, duration: float = 0):
        """
        Log the result of an individual test with detailed information.
        
        Args:
            test_name: Name of the test being executed
            status: PASS, FAIL, or SKIP
            details: Detailed description of test results
            duration: Time taken to execute the test in seconds
        """
        self.test_results["total_tests"] += 1
        
        if status == "PASS":
            self.test_results["passed"] += 1
            icon = f"{Colors.GREEN}✓{Colors.END}"
            status_color = Colors.GREEN
        elif status == "FAIL":
            self.test_results["failed"] += 1
            icon = f"{Colors.RED}✗{Colors.END}"
            status_color = Colors.RED
            self.test_results["errors"].append(f"{test_name}: {details}")
        else:  # SKIP
            icon = f"{Colors.YELLOW}⚠{Colors.END}"
            status_color = Colors.YELLOW
        
        # Log to console with formatting
        print(f"{icon} {Colors.BOLD}{test_name}{Colors.END}")
        print(f"   Status: {status_color}{status}{Colors.END}")
        print(f"   Details: {details}")
        if duration > 0:
            print(f"   Duration: {duration:.2f}s")
        print()
        
        # Store detailed results
        self.test_results["test_details"].append({
            "name": test_name,
            "status": status,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })

    def test_aws_connectivity(self) -> bool:
        """
        Test basic AWS connectivity and service availability.
        
        Verifies that we can connect to AWS services and that the
        required resources (SES, Lambda) are accessible.
        
        Returns:
            bool: True if AWS connectivity is successful, False otherwise
        """
        print(f"{Colors.BOLD}{Colors.PURPLE}🔧 Testing AWS Connectivity{Colors.END}")
        print(f"{Colors.PURPLE}-" * 40 + Colors.END)
        
        start_time = time.time()
        
        try:
            # Test SES connectivity
            print("Testing SES service connectivity...")
            ses_response = self.ses_client.get_send_quota()
            print(f"  • SES Send Quota: {ses_response.get('Max24HourSend', 'Unknown')}")
            print(f"  • SES Sent Last 24h: {ses_response.get('SentLast24Hours', 'Unknown')}")
            
            # Test Lambda connectivity
            print("Testing Lambda service connectivity...")
            lambda_functions = self.lambda_client.list_functions(
                FunctionVersion='ALL',
                MaxItems=50
            )
            
            # Look for our invite function
            invite_function_found = False
            for func in lambda_functions.get('Functions', []):
                if 'SendInviteEmail' in func['FunctionName']:
                    invite_function_found = True
                    print(f"  • Found SendInviteEmail function: {func['FunctionName']}")
                    print(f"  • Runtime: {func['Runtime']}")
                    print(f"  • Last Modified: {func['LastModified']}")
                    break
            
            if not invite_function_found:
                raise Exception("SendInviteEmail Lambda function not found")
            
            duration = time.time() - start_time
            self.log_test_result(
                "AWS Connectivity Test",
                "PASS",
                "Successfully connected to SES and Lambda services",
                duration
            )
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "AWS Connectivity Test",
                "FAIL",
                f"AWS connectivity failed: {str(e)}",
                duration
            )
            return False

    def test_ses_verified_emails(self) -> bool:
        """
        Verify that required email addresses are verified in SES.
        
        Checks that both the sender (benefactor) email and recipient
        (test) emails are verified in SES sandbox mode.
        
        Returns:
            bool: True if all required emails are verified, False otherwise
        """
        print(f"{Colors.BOLD}{Colors.PURPLE}📧 Testing SES Email Verification{Colors.END}")
        print(f"{Colors.PURPLE}-" * 40 + Colors.END)
        
        start_time = time.time()
        
        try:
            # Get list of verified email addresses
            print("Retrieving verified email identities from SES...")
            verified_emails = self.ses_client.list_verified_email_addresses()
            verified_list = verified_emails.get('VerifiedEmailAddresses', [])
            
            print(f"Found {len(verified_list)} verified email addresses:")
            for email in verified_list:
                print(f"  • {email}")
            
            # Check if our test emails are verified
            missing_emails = []
            
            # Check benefactor email
            if self.benefactor_email not in verified_list:
                missing_emails.append(self.benefactor_email)
                print(f"{Colors.YELLOW}⚠ Benefactor email not verified: {self.benefactor_email}{Colors.END}")
            else:
                print(f"{Colors.GREEN}✓ Benefactor email verified: {self.benefactor_email}{Colors.END}")
            
            # Check test recipient emails
            for test_email in self.test_emails:
                if test_email not in verified_list:
                    missing_emails.append(test_email)
                    print(f"{Colors.YELLOW}⚠ Test email not verified: {test_email}{Colors.END}")
                else:
                    print(f"{Colors.GREEN}✓ Test email verified: {test_email}{Colors.END}")
            
            duration = time.time() - start_time
            
            if missing_emails:
                self.log_test_result(
                    "SES Email Verification Test",
                    "FAIL",
                    f"Missing verified emails: {', '.join(missing_emails)}. Please verify these in SES console.",
                    duration
                )
                return False
            else:
                self.log_test_result(
                    "SES Email Verification Test",
                    "PASS",
                    f"All required emails are verified in SES",
                    duration
                )
                return True
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "SES Email Verification Test",
                "FAIL",
                f"Failed to check SES verification: {str(e)}",
                duration
            )
            return False

    def test_api_endpoint_accessibility(self) -> bool:
        """
        Test that the API endpoint is accessible and responds correctly.
        
        Makes a basic request to the invite endpoint to verify it's
        deployed and responding, even without authentication.
        
        Returns:
            bool: True if endpoint is accessible, False otherwise
        """
        print(f"{Colors.BOLD}{Colors.PURPLE}🌐 Testing API Endpoint Accessibility{Colors.END}")
        print(f"{Colors.PURPLE}-" * 40 + Colors.END)
        
        start_time = time.time()
        
        try:
            print(f"Testing endpoint: {self.invite_endpoint}")
            print("Making OPTIONS request to check CORS configuration...")
            
            # Test OPTIONS request (CORS preflight)
            options_response = requests.options(
                self.invite_endpoint,
                timeout=10
            )
            
            print(f"  • OPTIONS Status Code: {options_response.status_code}")
            print(f"  • CORS Headers Present: {'Access-Control-Allow-Origin' in options_response.headers}")
            
            # Test POST request without auth (should get 401)
            print("Making POST request without authentication (expecting 401)...")
            post_response = requests.post(
                self.invite_endpoint,
                json={"test": "data"},
                timeout=10
            )
            
            print(f"  • POST Status Code: {post_response.status_code}")
            print(f"  • Response Headers: {dict(post_response.headers)}")
            
            duration = time.time() - start_time
            
            # We expect 401 for unauthenticated requests
            if post_response.status_code == 401:
                self.log_test_result(
                    "API Endpoint Accessibility Test",
                    "PASS",
                    f"Endpoint is accessible and properly secured (401 for unauth requests)",
                    duration
                )
                return True
            else:
                self.log_test_result(
                    "API Endpoint Accessibility Test",
                    "FAIL",
                    f"Unexpected status code: {post_response.status_code}. Expected 401 for unauth request.",
                    duration
                )
                return False
                
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            self.log_test_result(
                "API Endpoint Accessibility Test",
                "FAIL",
                f"Network error accessing endpoint: {str(e)}",
                duration
            )
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "API Endpoint Accessibility Test",
                "FAIL",
                f"Unexpected error: {str(e)}",
                duration
            )
            return False

    def test_lambda_function_direct(self) -> bool:
        """
        Test the Lambda function directly using AWS SDK.
        
        Invokes the SendInviteEmail Lambda function directly to test
        its functionality without going through API Gateway.
        
        Returns:
            bool: True if Lambda function executes successfully, False otherwise
        """
        print(f"{Colors.BOLD}{Colors.PURPLE}⚡ Testing Lambda Function Direct Invocation{Colors.END}")
        print(f"{Colors.PURPLE}-" * 40 + Colors.END)
        
        start_time = time.time()
        
        try:
            # Prepare test payload
            test_payload = {
                "body": json.dumps({
                    "benefactor_email": self.benefactor_email,
                    "invitee_email": self.test_emails[0]
                })
            }
            
            print(f"Invoking Lambda function with test payload...")
            print(f"  • Benefactor Email: {self.benefactor_email}")
            print(f"  • Invitee Email: {self.test_emails[0]}")
            
            # Find the exact function name
            functions = self.lambda_client.list_functions()
            function_name = None
            
            for func in functions['Functions']:
                if 'SendInviteEmail' in func['FunctionName']:
                    function_name = func['FunctionName']
                    break
            
            if not function_name:
                raise Exception("SendInviteEmail function not found")
            
            print(f"  • Function Name: {function_name}")
            
            # Invoke the function
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            status_code = response_payload.get('statusCode', 0)
            
            print(f"  • Lambda Status Code: {status_code}")
            print(f"  • Lambda Response: {json.dumps(response_payload, indent=2)}")
            
            duration = time.time() - start_time
            
            if status_code == 200:
                response_body = json.loads(response_payload.get('body', '{}'))
                invite_token = response_body.get('invite_token', 'Not found')
                
                self.log_test_result(
                    "Lambda Function Direct Test",
                    "PASS",
                    f"Lambda executed successfully. Invite token: {invite_token[:8]}...",
                    duration
                )
                return True
            else:
                self.log_test_result(
                    "Lambda Function Direct Test",
                    "FAIL",
                    f"Lambda returned error status: {status_code}. Response: {response_payload}",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Lambda Function Direct Test",
                "FAIL",
                f"Lambda invocation failed: {str(e)}",
                duration
            )
            return False

    def test_error_scenarios(self) -> bool:
        """
        Test various error scenarios and edge cases.
        
        Tests how the system handles invalid inputs, missing data,
        and other error conditions to ensure robust error handling.
        
        Returns:
            bool: True if all error scenarios are handled correctly, False otherwise
        """
        print(f"{Colors.BOLD}{Colors.PURPLE}🚨 Testing Error Scenarios{Colors.END}")
        print(f"{Colors.PURPLE}-" * 40 + Colors.END)
        
        start_time = time.time()
        error_tests_passed = 0
        total_error_tests = 0
        
        # Test scenarios with expected outcomes
        error_scenarios = [
            {
                "name": "Missing benefactor_email",
                "payload": {"invitee_email": self.test_emails[0]},
                "expected_status": 400
            },
            {
                "name": "Missing invitee_email", 
                "payload": {"benefactor_email": self.benefactor_email},
                "expected_status": 400
            },
            {
                "name": "Invalid email format",
                "payload": {
                    "benefactor_email": "invalid-email",
                    "invitee_email": "also-invalid"
                },
                "expected_status": 500  # SES will reject invalid emails
            },
            {
                "name": "Empty payload",
                "payload": {},
                "expected_status": 400
            }
        ]
        
        try:
            # Find the Lambda function name
            functions = self.lambda_client.list_functions()
            function_name = None
            
            for func in functions['Functions']:
                if 'SendInviteEmail' in func['FunctionName']:
                    function_name = func['FunctionName']
                    break
            
            if not function_name:
                raise Exception("SendInviteEmail function not found")
            
            # Test each error scenario
            for scenario in error_scenarios:
                total_error_tests += 1
                print(f"Testing: {scenario['name']}")
                
                test_payload = {
                    "body": json.dumps(scenario['payload'])
                }
                
                try:
                    response = self.lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='RequestResponse',
                        Payload=json.dumps(test_payload)
                    )
                    
                    response_payload = json.loads(response['Payload'].read())
                    actual_status = response_payload.get('statusCode', 0)
                    
                    print(f"  • Expected Status: {scenario['expected_status']}")
                    print(f"  • Actual Status: {actual_status}")
                    
                    if actual_status == scenario['expected_status']:
                        print(f"  {Colors.GREEN}✓ Error handled correctly{Colors.END}")
                        error_tests_passed += 1
                    else:
                        print(f"  {Colors.RED}✗ Unexpected status code{Colors.END}")
                        
                except Exception as e:
                    print(f"  {Colors.RED}✗ Error during test: {str(e)}{Colors.END}")
                
                print()
            
            duration = time.time() - start_time
            
            if error_tests_passed == total_error_tests:
                self.log_test_result(
                    "Error Scenarios Test",
                    "PASS",
                    f"All {total_error_tests} error scenarios handled correctly",
                    duration
                )
                return True
            else:
                self.log_test_result(
                    "Error Scenarios Test",
                    "FAIL",
                    f"Only {error_tests_passed}/{total_error_tests} error scenarios handled correctly",
                    duration
                )
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(
                "Error Scenarios Test",
                "FAIL",
                f"Error testing scenarios: {str(e)}",
                duration
            )
            return False

    def generate_final_report(self):
        """
        Generate and display a comprehensive final test report.
        
        Summarizes all test results, performance metrics, and provides
        recommendations for any issues found during testing.
        """
        end_time = datetime.now()
        total_duration = (end_time - self.test_results["start_time"]).total_seconds()
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}📊 FINAL TEST REPORT{Colors.END}")
        print(f"{Colors.BLUE}=" * 70 + Colors.END)
        
        # Summary statistics
        print(f"{Colors.BOLD}Test Summary:{Colors.END}")
        print(f"  • Total Tests: {self.test_results['total_tests']}")
        print(f"  • Passed: {Colors.GREEN}{self.test_results['passed']}{Colors.END}")
        print(f"  • Failed: {Colors.RED}{self.test_results['failed']}{Colors.END}")
        print(f"  • Success Rate: {(self.test_results['passed']/self.test_results['total_tests']*100):.1f}%")
        print(f"  • Total Duration: {total_duration:.2f}s")
        print()
        
        # Overall status
        if self.test_results['failed'] == 0:
            print(f"{Colors.BOLD}{Colors.GREEN}🎉 ALL TESTS PASSED - INVITE SYSTEM IS READY!{Colors.END}")
        else:
            print(f"{Colors.BOLD}{Colors.RED}❌ SOME TESTS FAILED - REVIEW REQUIRED{Colors.END}")
        
        # Error details if any
        if self.test_results['errors']:
            print(f"\n{Colors.BOLD}{Colors.RED}Errors Found:{Colors.END}")
            for i, error in enumerate(self.test_results['errors'], 1):
                print(f"  {i}. {error}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}Recommendations:{Colors.END}")
        
        if self.test_results['failed'] == 0:
            print(f"  {Colors.GREEN}✓ Invite system is fully functional and ready for production use{Colors.END}")
            print(f"  {Colors.GREEN}✓ All AWS services are properly configured{Colors.END}")
            print(f"  {Colors.GREEN}✓ Error handling is working correctly{Colors.END}")
        else:
            print(f"  {Colors.YELLOW}⚠ Review failed tests and fix issues before production deployment{Colors.END}")
            if any("verification" in error.lower() for error in self.test_results['errors']):
                print(f"  {Colors.YELLOW}⚠ Verify email addresses in SES console{Colors.END}")
            if any("connectivity" in error.lower() for error in self.test_results['errors']):
                print(f"  {Colors.YELLOW}⚠ Check AWS credentials and permissions{Colors.END}")
        
        print(f"\n{Colors.CYAN}Next Steps:{Colors.END}")
        print(f"  1. If all tests passed, proceed with UI testing")
        print(f"  2. Test the complete flow from benefactor dashboard")
        print(f"  3. Verify email delivery to actual recipients")
        print(f"  4. Monitor CloudWatch logs for any issues")
        
        print(f"\n{Colors.BLUE}=" * 70 + Colors.END)

    def run_full_test_suite(self):
        """
        Execute the complete test suite with all test scenarios.
        
        Runs all tests in sequence and generates a comprehensive report
        of the invite system's functionality and readiness.
        """
        print(f"{Colors.BOLD}{Colors.CYAN}🧪 STARTING COMPREHENSIVE INVITE SYSTEM TEST SUITE{Colors.END}")
        print(f"{Colors.CYAN}=" * 70 + Colors.END)
        print(f"Start Time: {self.test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Configuration: Virtual Legacy MVP Invite System")
        print()
        
        # Execute all test phases
        tests_to_run = [
            ("AWS Connectivity", self.test_aws_connectivity),
            ("SES Email Verification", self.test_ses_verified_emails),
            ("API Endpoint Accessibility", self.test_api_endpoint_accessibility),
            ("Lambda Function Direct", self.test_lambda_function_direct),
            ("Error Scenarios", self.test_error_scenarios)
        ]
        
        for test_name, test_function in tests_to_run:
            print(f"{Colors.BOLD}Running: {test_name}{Colors.END}")
            try:
                test_function()
            except Exception as e:
                self.log_test_result(
                    test_name,
                    "FAIL",
                    f"Unexpected error during test execution: {str(e)}"
                )
            
            # Small delay between tests for readability
            time.sleep(1)
        
        # Generate final report
        self.generate_final_report()

def main():
    """
    Main entry point for the test suite.
    
    Initializes the test suite and runs all tests with proper
    error handling and cleanup.
    """
    try:
        # Create and run the test suite
        tester = InviteSystemTester()
        tester.run_full_test_suite()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test suite interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error in test suite: {str(e)}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()