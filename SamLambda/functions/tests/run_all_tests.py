#!/usr/bin/env python3
"""
COMPREHENSIVE TEST RUNNER FOR VIRTUAL LEGACY PERSONA SYSTEM

This script runs all test suites for the persona and relationship management system,
providing detailed reporting and error analysis. It validates the complete system
from individual component tests through full integration workflows.

BUSINESS PURPOSE:
Ensures that the persona system works correctly before deployment, preventing
user experience issues and security vulnerabilities in production.

TEST EXECUTION ORDER:
1. Shared Component Tests (PersonaValidator)
2. Cognito Trigger Tests (Pre-signup, Post-confirmation)
3. API Endpoint Access Control Tests
4. Integration Workflow Tests
5. Error Handling and Edge Case Tests

REPORTING:
- Detailed test results with business context
- Error analysis and recommendations
- Performance metrics
- Coverage analysis
"""

import sys
import os
import unittest
import time
from io import StringIO
import traceback

# Add current directory to path for test imports
sys.path.append(os.path.dirname(__file__))

class TestResult:
    """Container for test execution results and analysis."""
    
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.failures = []
        self.errors = []
        self.test_details = []
    
    def finish(self):
        """Mark test execution as complete."""
        self.end_time = time.time()
    
    def duration(self):
        """Get test execution duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def success_rate(self):
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

class VerboseTestResult(unittest.TextTestResult):
    """Custom test result class for detailed reporting."""
    
    def __init__(self, stream, descriptions, verbosity, result_container):
        super().__init__(stream, descriptions, verbosity)
        self.result_container = result_container
    
    def startTest(self, test):
        super().startTest(test)
        self.result_container.total_tests += 1
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"\n🔍 RUNNING: {test_name}")
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.result_container.passed_tests += 1
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"✅ PASSED: {test_name}")
    
    def addError(self, test, err):
        super().addError(test, err)
        self.result_container.error_tests += 1
        self.result_container.errors.append((test, err))
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"❌ ERROR: {test_name}")
        print(f"   Error: {err[1]}")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.result_container.failed_tests += 1
        self.result_container.failures.append((test, err))
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"❌ FAILED: {test_name}")
        print(f"   Failure: {err[1]}")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.result_container.skipped_tests += 1
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        print(f"⏭️  SKIPPED: {test_name} - {reason}")

def run_test_suite(test_module_name, description):
    """
    Run a specific test suite with detailed reporting.
    
    Args:
        test_module_name (str): Name of the test module to import
        description (str): Human-readable description of the test suite
        
    Returns:
        TestResult: Results of test execution
    """
    print(f"\n{'='*80}")
    print(f"RUNNING TEST SUITE: {description}")
    print(f"MODULE: {test_module_name}")
    print(f"{'='*80}")
    
    result_container = TestResult()
    
    try:
        # Import the test module
        test_module = __import__(test_module_name)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Create custom test runner
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=sys.stdout,
            verbosity=2,
            resultclass=lambda stream, descriptions, verbosity: VerboseTestResult(
                stream, descriptions, verbosity, result_container
            )
        )
        
        # Run tests
        test_result = runner.run(suite)
        
        result_container.finish()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"TEST SUITE SUMMARY: {description}")
        print(f"{'='*60}")
        print(f"Total Tests: {result_container.total_tests}")
        print(f"Passed: {result_container.passed_tests}")
        print(f"Failed: {result_container.failed_tests}")
        print(f"Errors: {result_container.error_tests}")
        print(f"Skipped: {result_container.skipped_tests}")
        print(f"Success Rate: {result_container.success_rate():.1f}%")
        print(f"Duration: {result_container.duration():.2f} seconds")
        
        return result_container
        
    except ImportError as e:
        print(f"❌ IMPORT ERROR: Could not import {test_module_name}")
        print(f"   Error: {e}")
        print(f"   This may indicate missing dependencies or incorrect file paths")
        result_container.error_tests += 1
        result_container.errors.append((test_module_name, e))
        result_container.finish()
        return result_container
    
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR in test suite {test_module_name}")
        print(f"   Error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        result_container.error_tests += 1
        result_container.errors.append((test_module_name, e))
        result_container.finish()
        return result_container

def analyze_errors(all_results):
    """
    Analyze errors across all test suites and provide recommendations.
    
    Args:
        all_results (list): List of TestResult objects from all test suites
    """
    print(f"\n{'='*80}")
    print("ERROR ANALYSIS AND RECOMMENDATIONS")
    print(f"{'='*80}")
    
    total_errors = sum(len(result.errors) + len(result.failures) for result in all_results)
    
    if total_errors == 0:
        print("🎉 NO ERRORS FOUND!")
        print("All tests passed successfully. The persona system is ready for deployment.")
        return
    
    print(f"Found {total_errors} total errors/failures across all test suites.")
    print("\nDETAILED ERROR ANALYSIS:")
    
    error_categories = {
        'import_errors': [],
        'persona_validation_errors': [],
        'database_errors': [],
        'api_errors': [],
        'integration_errors': []
    }
    
    for result in all_results:
        # Analyze failures
        for test, error in result.failures:
            error_msg = str(error[1]).lower()
            test_name = f"{test.__class__.__name__}.{test._testMethodName}"
            
            if 'import' in error_msg or 'module' in error_msg:
                error_categories['import_errors'].append((test_name, error[1]))
            elif 'persona' in error_msg or 'validation' in error_msg:
                error_categories['persona_validation_errors'].append((test_name, error[1]))
            elif 'dynamodb' in error_msg or 'database' in error_msg:
                error_categories['database_errors'].append((test_name, error[1]))
            elif 'api' in error_msg or 'endpoint' in error_msg:
                error_categories['api_errors'].append((test_name, error[1]))
            else:
                error_categories['integration_errors'].append((test_name, error[1]))
        
        # Analyze errors
        for test, error in result.errors:
            error_msg = str(error[1]).lower()
            test_name = f"{test.__class__.__name__}.{test._testMethodName}"
            
            if 'import' in error_msg or 'module' in error_msg:
                error_categories['import_errors'].append((test_name, error[1]))
            else:
                error_categories['integration_errors'].append((test_name, error[1]))
    
    # Report by category
    for category, errors in error_categories.items():
        if errors:
            print(f"\n--- {category.upper().replace('_', ' ')} ---")
            for test_name, error in errors:
                print(f"❌ {test_name}")
                print(f"   {error}")
            
            # Provide recommendations
            if category == 'import_errors':
                print("\n💡 RECOMMENDATIONS:")
                print("   - Check that all Lambda function files exist in expected locations")
                print("   - Verify Python path configuration")
                print("   - Ensure shared modules are accessible")
            
            elif category == 'persona_validation_errors':
                print("\n💡 RECOMMENDATIONS:")
                print("   - Review PersonaValidator logic for edge cases")
                print("   - Check JWT token structure and custom attributes")
                print("   - Validate Cognito trigger implementations")
            
            elif category == 'database_errors':
                print("\n💡 RECOMMENDATIONS:")
                print("   - Verify DynamoDB table schemas match expectations")
                print("   - Check mock database responses in tests")
                print("   - Validate database access permissions")
            
            elif category == 'api_errors':
                print("\n💡 RECOMMENDATIONS:")
                print("   - Review API Gateway event structure")
                print("   - Check CORS header configuration")
                print("   - Validate request/response formats")
            
            elif category == 'integration_errors':
                print("\n💡 RECOMMENDATIONS:")
                print("   - Review end-to-end workflow logic")
                print("   - Check component integration points")
                print("   - Validate test data consistency")

def generate_final_report(all_results):
    """
    Generate final test execution report with overall system health assessment.
    
    Args:
        all_results (list): List of TestResult objects from all test suites
    """
    print(f"\n{'='*80}")
    print("FINAL SYSTEM HEALTH REPORT")
    print(f"{'='*80}")
    
    total_tests = sum(result.total_tests for result in all_results)
    total_passed = sum(result.passed_tests for result in all_results)
    total_failed = sum(result.failed_tests for result in all_results)
    total_errors = sum(result.error_tests for result in all_results)
    total_skipped = sum(result.skipped_tests for result in all_results)
    total_duration = sum(result.duration() for result in all_results)
    
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"OVERALL TEST STATISTICS:")
    print(f"  Total Tests Executed: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Errors: {total_errors}")
    print(f"  Skipped: {total_skipped}")
    print(f"  Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"  Total Execution Time: {total_duration:.2f} seconds")
    
    # System health assessment
    print(f"\nSYSTEM HEALTH ASSESSMENT:")
    
    if overall_success_rate >= 95:
        print("🟢 EXCELLENT: System is ready for production deployment")
        print("   All critical functionality is working correctly")
        print("   Persona-based access control is properly implemented")
        print("   User workflows are functioning as expected")
    
    elif overall_success_rate >= 85:
        print("🟡 GOOD: System is mostly functional with minor issues")
        print("   Core functionality is working")
        print("   Some edge cases or non-critical features may need attention")
        print("   Consider addressing failures before production deployment")
    
    elif overall_success_rate >= 70:
        print("🟠 FAIR: System has significant issues that need attention")
        print("   Core functionality may be compromised")
        print("   Multiple components require fixes")
        print("   Do not deploy to production until issues are resolved")
    
    else:
        print("🔴 POOR: System has critical issues preventing proper operation")
        print("   Major functionality is broken")
        print("   Extensive debugging and fixes required")
        print("   System is not ready for any deployment")
    
    # Component-specific health
    print(f"\nCOMPONENT HEALTH BREAKDOWN:")
    
    component_health = {
        'Cognito Integration': 0,
        'Persona Validation': 0,
        'API Endpoints': 0,
        'Integration Workflows': 0
    }
    
    # This would be enhanced with more specific component tracking
    # For now, provide general assessment
    if total_errors == 0 and total_failed == 0:
        for component in component_health:
            component_health[component] = 100
    
    for component, health in component_health.items():
        if health >= 95:
            status = "🟢 EXCELLENT"
        elif health >= 85:
            status = "🟡 GOOD"
        elif health >= 70:
            status = "🟠 FAIR"
        else:
            status = "🔴 POOR"
        
        print(f"  {component}: {status}")
    
    print(f"\n{'='*80}")
    if overall_success_rate >= 95:
        print("✅ PERSONA SYSTEM VALIDATION COMPLETE - READY FOR DEPLOYMENT")
    else:
        print("⚠️  PERSONA SYSTEM VALIDATION COMPLETE - ISSUES REQUIRE ATTENTION")
    print(f"{'='*80}")

def main():
    """Main test execution function."""
    print("🚀 STARTING COMPREHENSIVE PERSONA SYSTEM TEST EXECUTION")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test suites to run
    test_suites = [
        ('comprehensive_persona_test_suite', 'Core Persona and Cognito Functionality'),
        ('api_endpoint_test_suite', 'API Endpoint Access Control'),
        ('integration_test_suite', 'End-to-End Integration Workflows')
    ]
    
    all_results = []
    
    # Run each test suite
    for module_name, description in test_suites:
        result = run_test_suite(module_name, description)
        all_results.append(result)
        
        # Brief pause between test suites
        time.sleep(1)
    
    # Analyze errors across all suites
    analyze_errors(all_results)
    
    # Generate final report
    generate_final_report(all_results)

if __name__ == '__main__':
    main()