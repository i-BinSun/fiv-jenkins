#!/usr/bin/env python3
"""
Test Runner Script with Failure Collection

This script runs unittest tests, collects all failures with stack traces,
and outputs a JSON report that can be used for email notification.
"""

import unittest
import sys
import json
import traceback
import io
from datetime import datetime
from pathlib import Path


class TestResultCollector(unittest.TestResult):
    """Custom TestResult class to collect detailed failure information"""
    
    def __init__(self):
        super().__init__()
        self.failures_detail = []
        self.errors_detail = []
        self.successes = []
        self.test_results = []
        self.start_time = None
        self.end_time = None
    
    def startTestRun(self):
        """Called once before any tests are executed"""
        self.start_time = datetime.now()
    
    def stopTestRun(self):
        """Called once after all tests are executed"""
        self.end_time = datetime.now()
    
    def addSuccess(self, test):
        """Called when a test passes"""
        super().addSuccess(test)
        self.successes.append({
            "test_name": str(test),
            "test_class": test.__class__.__name__,
            "test_method": test._testMethodName,
            "status": "PASSED"
        })
        self.test_results.append({
            "test_name": str(test),
            "status": "PASSED"
        })
    
    def addFailure(self, test, err):
        """Called when a test fails (assertion error)"""
        super().addFailure(test, err)
        
        # Get the full stack trace
        exc_type, exc_value, exc_tb = err
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        failure_info = {
            "test_name": str(test),
            "test_class": test.__class__.__name__,
            "test_method": test._testMethodName,
            "test_doc": test.shortDescription() or "",
            "status": "FAILED",
            "error_type": exc_type.__name__,
            "error_message": str(exc_value),
            "stack_trace": stack_trace
        }
        self.failures_detail.append(failure_info)
        self.test_results.append({
            "test_name": str(test),
            "status": "FAILED",
            "error": str(exc_value)
        })
    
    def addError(self, test, err):
        """Called when a test raises an unexpected exception"""
        super().addError(test, err)
        
        exc_type, exc_value, exc_tb = err
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        error_info = {
            "test_name": str(test),
            "test_class": test.__class__.__name__,
            "test_method": test._testMethodName,
            "test_doc": test.shortDescription() or "",
            "status": "ERROR",
            "error_type": exc_type.__name__,
            "error_message": str(exc_value),
            "stack_trace": stack_trace
        }
        self.errors_detail.append(error_info)
        self.test_results.append({
            "test_name": str(test),
            "status": "ERROR",
            "error": str(exc_value)
        })
    
    def addSkip(self, test, reason):
        """Called when a test is skipped"""
        super().addSkip(test, reason)
        self.test_results.append({
            "test_name": str(test),
            "status": "SKIPPED",
            "reason": reason
        })
    
    def get_report(self):
        """Generate a comprehensive test report"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "summary": {
                "total": self.testsRun,
                "passed": len(self.successes),
                "failed": len(self.failures_detail),
                "errors": len(self.errors_detail),
                "skipped": len(self.skipped)
            },
            "all_passed": len(self.failures_detail) == 0 and len(self.errors_detail) == 0,
            "failures": self.failures_detail,
            "errors": self.errors_detail,
            "test_results": self.test_results
        }


def discover_and_run_tests(test_dir="tests", pattern="test_*.py"):
    """
    Discover and run all tests in the specified directory
    
    Args:
        test_dir: Directory containing test files
        pattern: Pattern to match test files
    
    Returns:
        dict: Test report with all results and failures
    """
    # Create test loader and result collector
    loader = unittest.TestLoader()
    result = TestResultCollector()
    
    # Discover tests
    try:
        test_suite = loader.discover(test_dir, pattern=pattern)
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"Failed to discover tests: {str(e)}",
            "all_passed": False
        }
    
    # Run tests
    result.startTestRun()
    test_suite.run(result)
    result.stopTestRun()
    
    return result.get_report()


def save_report(report, output_file="test_report.json"):
    """Save the test report to a JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved to: {output_file}")


def print_summary(report):
    """Print a human-readable summary to console"""
    summary = report.get("summary", {})
    
    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Timestamp: {report.get('timestamp', 'N/A')}")
    print(f"Duration: {report.get('duration_seconds', 'N/A'):.2f} seconds")
    print("-" * 60)
    print(f"Total Tests:  {summary.get('total', 0)}")
    print(f"Passed:       {summary.get('passed', 0)}")
    print(f"Failed:       {summary.get('failed', 0)}")
    print(f"Errors:       {summary.get('errors', 0)}")
    print(f"Skipped:      {summary.get('skipped', 0)}")
    print("-" * 60)
    
    if report.get("all_passed"):
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
        
        # Print failure details
        if report.get("failures"):
            print("\n" + "-" * 60)
            print("FAILURES:")
            print("-" * 60)
            for failure in report["failures"]:
                print(f"\n🔴 {failure['test_name']}")
                print(f"   Class: {failure['test_class']}")
                print(f"   Method: {failure['test_method']}")
                print(f"   Error: {failure['error_message']}")
                print(f"\n   Stack Trace:")
                for line in failure['stack_trace'].split('\n'):
                    print(f"   {line}")
        
        # Print error details
        if report.get("errors"):
            print("\n" + "-" * 60)
            print("ERRORS:")
            print("-" * 60)
            for error in report["errors"]:
                print(f"\n🟠 {error['test_name']}")
                print(f"   Class: {error['test_class']}")
                print(f"   Method: {error['test_method']}")
                print(f"   Error Type: {error['error_type']}")
                print(f"   Error: {error['error_message']}")
                print(f"\n   Stack Trace:")
                for line in error['stack_trace'].split('\n'):
                    print(f"   {line}")
    
    print("=" * 60 + "\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests and collect failure information')
    parser.add_argument('--test-dir', default='tests', help='Directory containing tests')
    parser.add_argument('--pattern', default='test_*.py', help='Test file pattern')
    parser.add_argument('--output', default='test_report.json', help='Output JSON file')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')
    
    args = parser.parse_args()
    
    # Run tests
    report = discover_and_run_tests(args.test_dir, args.pattern)
    
    # Save report
    save_report(report, args.output)
    
    # Print summary
    if not args.quiet:
        print_summary(report)
    
    # Exit with appropriate code
    if report.get("all_passed"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
