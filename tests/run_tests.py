#!/usr/bin/env python3
"""
Test runner script for FileValidator tests

Runs the comprehensive test suite for FileValidator module
with proper environment setup and reporting.

Usage:
    python tests/run_tests.py
    python tests/run_tests.py --verbose
    python tests/run_tests.py --specific test_file_validator.py::TestFileValidator::test_load_schema_file_exists
"""

import sys
import os
import pytest
import argparse

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


def run_tests(args=None):
    """
    Run the test suite with appropriate configuration
    
    Args:
        args: Command line arguments (optional)
    """
    
    # Default pytest arguments
    pytest_args = [
        'tests/',  # Test directory
        '-v',      # Verbose output
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker handling
        '--disable-warnings',  # Disable pytest warnings for cleaner output
    ]
    
    # Parse command line arguments if provided
    if args:
        if '--verbose' in args:
            pytest_args.append('-vv')  # Extra verbose
        if '--specific' in args:
            # Allow running specific tests
            specific_idx = args.index('--specific')
            if specific_idx + 1 < len(args):
                pytest_args = [args[specific_idx + 1]] + pytest_args[1:]  # Replace test directory
    
    # Set environment variables for testing
    os.environ.setdefault('PROJECT_ID', 'test-project')
    
    print("=" * 60)
    print("Running FileValidator Test Suite")
    print("=" * 60)
    print(f"Project Root: {project_root}")
    print(f"Test Command: pytest {' '.join(pytest_args)}")
    print("=" * 60)
    
    # Run the tests
    exit_code = pytest.main(pytest_args)
    
    print("=" * 60)
    if exit_code == 0:
        print("✅ All tests passed successfully!")
    else:
        print(f"❌ Tests failed with exit code: {exit_code}")
    print("=" * 60)
    
    return exit_code


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description='Run FileValidator tests')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--specific', type=str, help='Run specific test (e.g., test_file_validator.py::TestFileValidator::test_load_schema)')
    
    args = parser.parse_args()
    
    # Convert args to list for compatibility
    arg_list = []
    if args.verbose:
        arg_list.append('--verbose')
    if args.specific:
        arg_list.extend(['--specific', args.specific])
    
    exit_code = run_tests(arg_list)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()