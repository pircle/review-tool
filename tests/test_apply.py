"""
Unit tests for the fix application functionality.
"""

import os
import shutil
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

from ai_review.apply import FixApplier, CodeFixer


class TestCodeFixer(unittest.TestCase):
    def setUp(self):
        """Create a temporary test file."""
        self.test_file = "test_code.py"
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('Hello, world!')\n")

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_file + ".bak"):
            os.remove(self.test_file + ".bak")

    def test_apply_fixes(self):
        """Test that fixes are correctly applied."""
        fixer = CodeFixer(self.test_file)
        suggestions = {
            "suggestions": [
                {
                    "title": "Update greeting",
                    "location": "Line 2",
                    "improvement": "    print('Hello, AI!')"
                }
            ]
        }
        result = fixer.apply_fixes(suggestions)

        self.assertTrue(result.get("success", False))
        
        with open(self.test_file, "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[1].strip(), "    print('Hello, AI!')")

    def test_backup_creation(self):
        """Ensure that a backup file is created."""
        fixer = CodeFixer(self.test_file)
        suggestions = {
            "suggestions": [
                {
                    "title": "Update greeting",
                    "location": "Line 2",
                    "improvement": "    print('Hello, AI!')"
                }
            ]
        }
        fixer.apply_fixes(suggestions)

        self.assertTrue(os.path.exists(self.test_file + ".bak"))
        
        # Verify backup contains original content
        with open(self.test_file + ".bak", "r") as f:
            content = f.read()
        
        self.assertEqual(content, "def hello():\n    print('Hello, world!')\n")

    def test_multiple_fixes(self):
        """Test applying multiple fixes to a file."""
        with open(self.test_file, "w") as f:
            f.write("def hello():\n    print('Hello, world!')\n\ndef goodbye():\n    print('Goodbye, world!')\n")
            
        fixer = CodeFixer(self.test_file)
        suggestions = {
            "suggestions": [
                {
                    "title": "Update hello greeting",
                    "location": "Line 2",
                    "improvement": "    print('Hello, AI!')"
                },
                {
                    "title": "Update goodbye greeting",
                    "location": "Line 4",
                    "improvement": "    print('Goodbye, AI!')"
                }
            ]
        }
        result = fixer.apply_fixes(suggestions)

        self.assertTrue(result.get("success", False))
        self.assertEqual(len(result.get("applied_fixes", [])), 2)
        
        with open(self.test_file, "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[1].strip(), "    print('Hello, AI!')")
        self.assertEqual(lines[3].strip(), "    print('Goodbye, AI!')")


class TestFixApplier(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_file = "test_complex.py"
        with open(self.test_file, "w") as f:
            f.write("""def complex_function(a, b, c):
    result = 0
    if a > 0:
        if b > 0:
            if c > 0:
                result = a + b + c
            else:
                result = a + b
        else:
            result = a
    return result
""")

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_file + ".bak"):
            os.remove(self.test_file + ".bak")

    @patch('ai_review.apply.OpenAI')
    def test_apply_ai_fixes(self, mock_openai):
        """Test that AI fixes are correctly applied."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Create a mock response for the OpenAI API
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """```python
def complex_function(a, b, c):
    # Simplified function with early returns
    if a <= 0:
        return a
    if b <= 0:
        return a
    if c <= 0:
        return a + b
    return a + b + c
```"""
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create AI review with a suggestion for the complex function
        ai_review = {
            "suggestions": [
                {
                    "title": "Simplify complex function",
                    "severity": "medium",
                    "location": "Function: complex_function",
                    "description": "The function has too many nested if statements",
                    "improvement": "Use early returns to simplify the logic"
                }
            ]
        }
        
        # Apply the fixes
        applier = FixApplier(api_key="dummy_key")
        result = applier.apply_ai_fixes(self.test_file, ai_review)
        
        # Verify the result
        self.assertTrue(result.get("success", False))
        self.assertEqual(len(result.get("applied_fixes", [])), 1)
        
        # Check that the file was modified correctly
        with open(self.test_file, "r") as f:
            content = f.read()
        
        self.assertIn("# Simplified function with early returns", content)
        self.assertIn("if a <= 0:", content)
        self.assertIn("return a + b + c", content)
        
    def test_extract_line_numbers(self):
        """Test the _extract_line_numbers method."""
        applier = FixApplier()
        
        # Test with line format
        line_nums = applier._extract_line_numbers("Line 5")
        self.assertEqual(line_nums, [5])
        
        # Test with range format
        line_nums = applier._extract_line_numbers("Lines 5-10")
        self.assertEqual(line_nums, [5, 6, 7, 8, 9, 10])
        
        # Test with invalid format
        line_nums = applier._extract_line_numbers("Invalid location")
        self.assertEqual(line_nums, [])
        
    def test_extract_function_name(self):
        """Test the _extract_function_name method."""
        applier = FixApplier()
        
        # Test with function format
        func_name = applier._extract_function_name("Function: test_function")
        self.assertEqual(func_name, "test_function")
        
        # Test with method format
        func_name = applier._extract_function_name("Method: TestClass.test_method")
        self.assertEqual(func_name, "test_method")
        
        # Test with invalid format
        func_name = applier._extract_function_name("Invalid location")
        self.assertIsNone(func_name)
        
    def test_apply_line_fix(self):
        """Test the _apply_line_fix method."""
        applier = FixApplier()
        
        code = "line1\nline2\nline3\nline4\n"
        fixed_code = applier._apply_line_fix(code, [2], "new_line2")
        
        self.assertEqual(fixed_code, "line1\nnew_line2\nline3\nline4\n")
        
        # Test with multiple lines
        fixed_code = applier._apply_line_fix(code, [2, 3], "new_line2_and_3")
        
        self.assertEqual(fixed_code, "line1\nnew_line2_and_3\nline4\n")
        
    def test_apply_function_fix(self):
        """Test the _apply_function_fix method."""
        applier = FixApplier()
        
        code = """def func1():
    print("func1")
    
def target_func():
    print("old implementation")
    return None
    
def func3():
    print("func3")
"""
        
        new_implementation = """def target_func():
    print("new implementation")
    return True"""
        
        fixed_code = applier._apply_function_fix(code, "target_func", new_implementation)
        
        self.assertIn("def func1():", fixed_code)
        self.assertIn("print(\"new implementation\")", fixed_code)
        self.assertIn("return True", fixed_code)
        self.assertIn("def func3():", fixed_code)
        self.assertNotIn("print(\"old implementation\")", fixed_code)


if __name__ == "__main__":
    unittest.main() 