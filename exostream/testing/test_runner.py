"""
Test runner for Exostream
Runs all tests and provides simple pass/fail reporting
"""

import unittest
import sys
import io
from pathlib import Path
from typing import Tuple


class SimpleTestResult(unittest.TestResult):
    """Custom test result that tracks test execution"""
    
    def __init__(self):
        super().__init__()
        self.test_results = []
    
    def startTest(self, test):
        super().startTest(test)
        self.current_test = str(test)
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append((str(test), 'PASS', None))
    
    def addError(self, test, err):
        super().addError(test, err)
        exc_type, exc_value, exc_tb = err
        self.test_results.append((str(test), 'ERROR', str(exc_value)))
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        exc_type, exc_value, exc_tb = err
        self.test_results.append((str(test), 'FAIL', str(exc_value)))
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_results.append((str(test), 'SKIP', reason))


def run_tests(verbose: bool = False) -> Tuple[bool, dict]:
    """
    Run all Exostream tests
    
    Args:
        verbose: If True, show detailed output
    
    Returns:
        Tuple of (success: bool, results: dict with stats)
    """
    # Find the tests directory
    project_root = Path(__file__).parent.parent.parent
    tests_dir = project_root / 'tests'
    
    if not tests_dir.exists():
        return False, {
            'error': 'Tests directory not found',
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0
        }
    
    # Discover tests
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir), pattern='test_*.py')
    
    # Run tests with custom result
    result = SimpleTestResult()
    
    # Capture stdout/stderr if not verbose
    if not verbose:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
    
    try:
        suite.run(result)
    finally:
        if not verbose:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Calculate statistics
    total = result.testsRun
    passed = len([r for r in result.test_results if r[1] == 'PASS'])
    failed = len([r for r in result.test_results if r[1] == 'FAIL'])
    errors = len([r for r in result.test_results if r[1] == 'ERROR'])
    skipped = len([r for r in result.test_results if r[1] == 'SKIP'])
    
    success = failed == 0 and errors == 0
    
    results = {
        'total': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'skipped': skipped,
        'test_results': result.test_results if verbose else []
    }
    
    return success, results


def format_test_name(test_str: str) -> str:
    """Format test name for display"""
    # Extract test name from full test string
    # Example: "test_daemon_starts (test_daemon.TestDaemon)" -> "test_daemon_starts"
    if '(' in test_str:
        name = test_str.split('(')[0].strip()
        module = test_str.split('(')[1].rstrip(')').split('.')[0]
        return f"{module}.{name}"
    return test_str

