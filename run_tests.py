#!/usr/bin/env python
"""
Script to run the unit tests for the AI code review system.
"""

import os
import sys
import subprocess


def run_tests(args=None):
    """
    Run the unit tests with the specified arguments.
    
    Args:
        args: Command-line arguments to pass to pytest
    """
    if args is None:
        args = []
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get the parent directory (project root)
    project_root = os.path.dirname(script_dir)
    
    # Change to the project root directory
    os.chdir(project_root)
    
    # Build the command
    cmd = ["pytest", "tests/"] + args
    
    # Run the tests
    result = subprocess.run(cmd, capture_output=False)
    
    return result.returncode


def main():
    """Main entry point."""
    # Get command-line arguments (excluding the script name)
    args = sys.argv[1:]
    
    # Run the tests
    return_code = run_tests(args)
    
    # Exit with the same return code
    sys.exit(return_code)


if __name__ == "__main__":
    main() 