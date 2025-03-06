"""
Unit tests for the CLI functionality related to fix application.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

from ai_review.cli import apply_ai_fixes, review_code


class TestCLI(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_file = "test_cli.py"
        with open(self.test_file, "w") as f:
            f.write("def test_function():\n    return 'test'\n")

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_file + ".bak"):
            os.remove(self.test_file + ".bak")

    @patch('ai_review.cli.FixApplier')
    def test_apply_ai_fixes(self, mock_fix_applier):
        """Test the apply_ai_fixes function."""
        # Mock the FixApplier class
        mock_instance = MagicMock()
        mock_fix_applier.return_value = mock_instance
        
        # Set up the mock to return a successful result
        mock_instance.apply_ai_fixes.return_value = {
            "success": True,
            "message": "Fixes applied successfully",
            "applied_fixes": [
                {
                    "title": "Test fix",
                    "location": "Line 2",
                    "severity": "medium"
                }
            ]
        }
        
        # Create a test AI review
        ai_review = {
            "suggestions": [
                {
                    "title": "Test fix",
                    "location": "Line 2",
                    "improvement": "    return 'fixed'"
                }
            ]
        }
        
        # Call the function
        result = apply_ai_fixes(self.test_file, ai_review, api_key="test_key")
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(len(result["applied_fixes"]), 1)
        
        # Verify that FixApplier was called with the correct arguments
        mock_fix_applier.assert_called_once_with(api_key="test_key", model="gpt-3.5-turbo")
        mock_instance.apply_ai_fixes.assert_called_once_with(self.test_file, ai_review)

    @patch('ai_review.cli.SuggestionGenerator')
    @patch('ai_review.cli.apply_ai_fixes')
    @patch('ai_review.cli.print_fix_results')
    @patch('sys.stdout', new_callable=StringIO)
    def test_review_code_with_apply_fixes(self, mock_stdout, mock_print_fix, mock_apply_fixes, mock_suggester):
        """Test the review_code function with apply_fixes=True."""
        # Mock the SuggestionGenerator
        mock_suggester_instance = MagicMock()
        mock_suggester.return_value = mock_suggester_instance
        
        # Set up the mock to return a successful AI review
        mock_suggester_instance.generate_ai_review.return_value = {
            "review": {
                "summary": "Test summary",
                "overall_quality": 8,
                "suggestions": [
                    {
                        "title": "Test fix",
                        "location": "Line 2",
                        "improvement": "    return 'fixed'"
                    }
                ]
            }
        }
        
        # Set up the mock for apply_ai_fixes
        mock_apply_fixes.return_value = {
            "success": True,
            "message": "Fixes applied successfully",
            "applied_fixes": [
                {
                    "title": "Test fix",
                    "location": "Line 2",
                    "severity": "medium"
                }
            ]
        }
        
        # Call the function
        review_code(
            path=self.test_file,
            ai=True,
            api_key="test_key",
            apply_fixes=True
        )
        
        # Verify that apply_ai_fixes was called
        mock_apply_fixes.assert_called_once()
        
        # Verify that print_fix_results was called
        mock_print_fix.assert_called_once()
        
        # Verify that the correct output was printed
        output = mock_stdout.getvalue()
        self.assertIn("Reviewing code at", output)
        self.assertIn("Generating AI-powered code review", output)
        self.assertIn("Applying AI-suggested fixes", output)


if __name__ == "__main__":
    unittest.main() 