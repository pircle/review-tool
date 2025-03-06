"""
Integration tests for the AI code review system.
"""

import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from ai_review.analyzer import analyze_file
from ai_review.suggestions import SuggestionGenerator
from ai_review.apply import FixApplier


class TestIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create a test file with some code
        self.test_file = os.path.join(self.test_dir, "test_integration.py")
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

def simple_function():
    print("Hello, world!")
    return None
""")

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir)

    @patch('ai_review.suggestions.OpenAI')
    @patch('ai_review.apply.OpenAI')
    def test_end_to_end_workflow(self, mock_apply_openai, mock_suggestions_openai):
        """Test the end-to-end workflow of analyze, suggest, and apply."""
        # Mock the OpenAI client for suggestions
        mock_suggestions_client = MagicMock()
        mock_suggestions_openai.return_value = mock_suggestions_client
        
        # Create a mock response for the suggestions API
        mock_suggestions_response = MagicMock()
        mock_suggestions_response.choices = [MagicMock()]
        mock_suggestions_response.choices[0].message.content = """
{
  "summary": "The code contains a complex function with nested if statements and a simple function.",
  "overall_quality": 6,
  "suggestions": [
    {
      "title": "Simplify complex function",
      "severity": "medium",
      "location": "Function: complex_function",
      "description": "The function has too many nested if statements which makes it hard to read and maintain.",
      "improvement": "Use early returns to simplify the logic and make the code more readable."
    },
    {
      "title": "Add docstring to simple_function",
      "severity": "low",
      "location": "Function: simple_function",
      "description": "The function lacks documentation.",
      "improvement": "Add a docstring to explain what the function does."
    }
  ],
  "best_practices": [
    "Use early returns to reduce nesting",
    "Add docstrings to all functions"
  ]
}
"""
        mock_suggestions_client.chat.completions.create.return_value = mock_suggestions_response
        
        # Mock the OpenAI client for apply
        mock_apply_client = MagicMock()
        mock_apply_openai.return_value = mock_apply_client
        
        # Create a mock response for the apply API
        mock_apply_response = MagicMock()
        mock_apply_response.choices = [MagicMock()]
        mock_apply_response.choices[0].message.content = """```python
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
        mock_apply_client.chat.completions.create.return_value = mock_apply_response
        
        # Step 1: Analyze the file
        analysis = analyze_file(self.test_file)
        
        # Verify analysis results
        self.assertEqual(len(analysis["functions"]), 2)
        self.assertIn("complex_function", [f["name"] for f in analysis["functions"]])
        self.assertIn("simple_function", [f["name"] for f in analysis["functions"]])
        
        # Step 2: Generate AI suggestions
        with open(self.test_file, 'r', encoding='utf-8') as file:
            code = file.read()
        
        suggester = SuggestionGenerator(api_key="dummy_key")
        ai_review = suggester.generate_ai_review(code, analysis)
        
        # Verify AI review
        self.assertIn("review", ai_review)
        review = ai_review["review"]
        self.assertEqual(len(review["suggestions"]), 2)
        
        # Step 3: Apply fixes
        applier = FixApplier(api_key="dummy_key")
        result = applier.apply_ai_fixes(self.test_file, review)
        
        # Verify fix application results
        self.assertTrue(result["success"])
        self.assertGreaterEqual(len(result["applied_fixes"]), 1)
        
        # Verify that a backup was created
        self.assertTrue(os.path.exists(self.test_file + ".bak"))
        
        # Verify that the file was modified
        with open(self.test_file, 'r', encoding='utf-8') as file:
            modified_code = file.read()
        
        self.assertIn("# Simplified function with early returns", modified_code)
        self.assertIn("if a <= 0:", modified_code)


if __name__ == "__main__":
    unittest.main() 