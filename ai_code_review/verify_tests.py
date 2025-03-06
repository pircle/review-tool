#!/usr/bin/env python3
"""
Script to verify that the tests are properly structured.
"""

import os
import sys
import importlib.util
import unittest


def import_module_from_file(file_path):
    """
    Import a module from a file path.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Imported module
    """
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_test_files():
    """
    Find all test files in the tests directory.
    
    Returns:
        List of test file paths
    """
    tests_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests")
    test_files = []
    
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))
    
    return test_files


def verify_tests():
    """
    Verify that the tests are properly structured.
    """
    test_files = find_test_files()
    
    if not test_files:
        print("No test files found.")
        return False
    
    print(f"Found {len(test_files)} test files:")
    for file in test_files:
        print(f"  - {os.path.basename(file)}")
    
    # Try to import each test file
    for file in test_files:
        try:
            module = import_module_from_file(file)
            test_classes = [cls for name, cls in vars(module).items() 
                           if isinstance(cls, type) and issubclass(cls, unittest.TestCase)]
            
            if not test_classes:
                print(f"Warning: No test classes found in {os.path.basename(file)}")
                continue
            
            print(f"\nTest classes in {os.path.basename(file)}:")
            for cls in test_classes:
                test_methods = [name for name in dir(cls) if name.startswith("test_")]
                print(f"  - {cls.__name__}: {len(test_methods)} test methods")
                for method in test_methods:
                    print(f"    - {method}")
        except Exception as e:
            print(f"Error importing {os.path.basename(file)}: {e}")
            return False
    
    return True


def main():
    """Main entry point."""
    success = verify_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 