"""
Module for generating code improvement suggestions using AI.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

# Get logger
from .logger import get_logger
logger = get_logger()

# Define system prompts as constants
SYSTEM_PROMPT_REVIEW = """
You are an expert software code reviewer with deep knowledge of programming best practices, design patterns, and clean code principles.
Your task is to review the provided code and provide actionable, specific suggestions for improvement.

Format your response as a structured JSON with the following sections:
1. "summary": A brief summary of the code and its purpose
2. "overall_quality": An assessment of the overall code quality (1-10)
3. "suggestions": A list of specific suggestions, each with:
   - "title": A short title for the suggestion
   - "description": Detailed explanation of the issue
   - "severity": "high", "medium", or "low"
   - "category": One of "security", "performance", "readability", "maintainability", "bug"
   - "location": Where in the code the issue is found (line numbers or function name)
   - "improvement": Specific code or approach to fix the issue
4. "best_practices": List of best practices that should be followed
5. "potential_bugs": Any potential bugs or edge cases identified

Focus on:
- Code organization and structure
- Function and variable naming
- Complexity reduction
- Performance improvements
- Security vulnerabilities
- Error handling
- Documentation
- Testability

IMPORTANT: Your response MUST be valid JSON. Do not include any text outside the JSON structure.
"""

SYSTEM_PROMPT_COMPLEX_FUNCTION = """
You are an expert code reviewer specializing in refactoring complex functions.
Analyze the provided function and suggest specific improvements to reduce complexity and improve readability.

Format your response as a structured JSON with the following sections:
1. "function_name": The name of the function being analyzed
2. "complexity_assessment": Brief assessment of why the function is complex
3. "suggestions": A list of specific suggestions, each with:
   - "title": A short title for the suggestion
   - "description": Detailed explanation of the issue
   - "improvement": Specific code or approach to fix the issue
4. "refactored_code": A complete refactored version of the function

Focus on:
- Reducing cyclomatic complexity
- Improving naming
- Adding proper documentation
- Breaking down into smaller functions
- Applying appropriate design patterns

IMPORTANT: Your response MUST be valid JSON. Do not include any text outside the JSON structure.
"""

SYSTEM_PROMPT_GENERAL = """
You are an expert code reviewer with deep knowledge of programming best practices.
Analyze the provided code and suggest general improvements for code quality.

Format your response as a structured JSON with the following sections:
1. "code_assessment": A brief assessment of the code quality
2. "suggestions": A list of specific suggestions, each with:
   - "title": A short title for the suggestion
   - "category": One of "style", "organization", "best_practices", "performance", "security"
   - "description": Detailed explanation of the issue
   - "improvement": Specific code or approach to fix the issue
3. "best_practices": List of best practices that should be followed

Focus on:
- Code organization
- Potential bugs or edge cases
- Performance improvements
- Following language-specific best practices
- Security considerations

IMPORTANT: Your response MUST be valid JSON. Do not include any text outside the JSON structure.
"""


class SuggestionGenerator:
    """Generates code improvement suggestions using AI."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the suggestion generator.
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
            model: OpenAI model to use (default: gpt-3.5-turbo)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        logger.info(f"Initialized SuggestionGenerator with model: {model}")
    
    def generate_suggestions(self, code: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate suggestions for improving the code.
        
        Args:
            code: Source code to analyze
            analysis: Analysis results from the analyzer
            
        Returns:
            List of suggestions
        """
        logger.info("Generating suggestions for code")
        suggestions = []
        
        # Generate suggestions for high complexity functions
        for func in analysis.get("functions", []):
            if func.get("complexity", 0) > 5:
                logger.debug(f"Generating suggestion for complex function: {func.get('name')}")
                suggestion = self._get_suggestion_for_complex_function(code, func)
                if suggestion:
                    suggestions.append(suggestion)
        
        # Generate general code quality suggestions
        logger.debug("Generating general code quality suggestions")
        general_suggestion = self._get_general_suggestions(code)
        if general_suggestion:
            suggestions.append(general_suggestion)
            
        logger.info(f"Generated {len(suggestions)} suggestions")
        return suggestions
    
    def generate_ai_review(self, code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive AI review of the code.
        
        Args:
            code: Source code to analyze
            analysis: Analysis results from the analyzer
            
        Returns:
            Dictionary with AI review results
        """
        try:
            logger.info("Generating comprehensive AI review")
            
            # Prepare a summary of the analysis for the AI
            functions_summary = []
            for func in analysis.get("functions", []):
                functions_summary.append({
                    "name": func.get("name", "unknown"),
                    "line_number": func.get("line_number", 0),
                    "complexity": func.get("complexity", 0),
                    "args": func.get("args", [])
                })
                
            classes_summary = []
            for cls in analysis.get("classes", []):
                classes_summary.append({
                    "name": cls.get("name", "unknown"),
                    "line_number": cls.get("line_number", 0),
                    "methods": cls.get("methods", []),
                    "complexity": cls.get("complexity", 0)
                })
                
            analysis_summary = {
                "file_path": analysis.get("file_path", "unknown"),
                "loc": analysis.get("loc", 0),
                "functions": functions_summary,
                "classes": classes_summary,
                "language": analysis.get("language", "python")
            }
            
            # Limit code size for API call
            code_sample = code[:8000] if len(code) > 8000 else code
            
            # Create a prompt for the AI
            user_prompt = f"""
            Here is the code to review:
            
            ```
            {code_sample}
            ```
            
            Here is the analysis of the code:
            
            ```json
            {json.dumps(analysis_summary, indent=2)}
            ```
            
            Please provide a comprehensive code review with specific, actionable suggestions for improvement.
            Remember to format your response as valid JSON according to the structure specified.
            """
            
            # Call the OpenAI API
            logger.debug("Calling OpenAI API for comprehensive review")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_REVIEW},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Extract the response
            ai_review_text = response.choices[0].message.content.strip()
            
            # Try to parse the response as JSON
            try:
                ai_review = json.loads(ai_review_text)
                logger.debug("Successfully parsed AI review response as JSON")
                
                # Validate the AI response
                if not self._validate_ai_response(ai_review):
                    logger.warning("AI response validation failed, some required fields are missing")
                    ai_review["validation_warning"] = "Response is missing some expected fields"
            except json.JSONDecodeError as e:
                # If the response is not valid JSON, return it as plain text
                logger.error(f"Failed to parse AI response as JSON: {e}")
                ai_review = {
                    "raw_response": ai_review_text,
                    "error": "Failed to parse AI response as JSON"
                }
            
            return {
                "type": "ai_review",
                "review": ai_review
            }
            
        except Exception as e:
            logger.error(f"Error generating AI review: {e}", exc_info=True)
            return {
                "type": "ai_review",
                "error": str(e)
            }
    
    def _validate_ai_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that the AI response contains the expected fields.
        
        Args:
            response: The AI response to validate
            
        Returns:
            True if the response is valid, False otherwise
        """
        required_keys = ["summary", "overall_quality", "suggestions"]
        return all(key in response for key in required_keys)
    
    def _get_suggestion_for_complex_function(self, code: str, func_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get suggestion for a complex function.
        
        Args:
            code: Source code
            func_info: Function information
            
        Returns:
            Suggestion or None if no suggestion
        """
        try:
            # Extract the function code
            lines = code.splitlines()
            func_name = func_info["name"]
            line_number = func_info["line_number"]
            
            logger.debug(f"Extracting code for function {func_name} at line {line_number}")
            
            # Find the function in the code
            function_code = self._extract_function_code(lines, line_number)
            
            # Generate suggestion using OpenAI
            user_prompt = f"""
            Analyze this function and suggest improvements for readability and maintainability:
            
            ```
            {function_code}
            ```
            
            Function name: {func_name}
            Complexity score: {func_info.get('complexity', 'Unknown')}
            
            Please provide specific, actionable suggestions to improve this function.
            Remember to format your response as valid JSON according to the structure specified.
            """
            
            logger.debug(f"Calling OpenAI API for function {func_name}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_COMPLEX_FUNCTION},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            suggestion_text = response.choices[0].message.content.strip()
            
            # Try to parse the response as JSON
            try:
                suggestion_json = json.loads(suggestion_text)
                logger.debug(f"Successfully parsed suggestion for function {func_name} as JSON")
                
                return {
                    "type": "complex_function",
                    "function_name": func_name,
                    "line_number": line_number,
                    "structured_suggestion": suggestion_json
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse suggestion for function {func_name} as JSON, using raw text")
                return {
                    "type": "complex_function",
                    "function_name": func_name,
                    "line_number": line_number,
                    "suggestion": suggestion_text
                }
                
        except Exception as e:
            logger.error(f"Error generating suggestion for function {func_info.get('name')}: {e}", exc_info=True)
            return None
    
    def _get_general_suggestions(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get general code quality suggestions.
        
        Args:
            code: Source code
            
        Returns:
            Suggestion or None if no suggestion
        """
        try:
            # Limit code size for API call
            code_sample = code[:5000] if len(code) > 5000 else code
            
            user_prompt = f"""
            Review this code and provide general suggestions for improvement:
            
            ```
            {code_sample}
            ```
            
            Please provide specific, actionable suggestions for improving code quality.
            Remember to format your response as valid JSON according to the structure specified.
            """
            
            logger.debug("Calling OpenAI API for general suggestions")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_GENERAL},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            suggestion_text = response.choices[0].message.content.strip()
            
            # Try to parse the response as JSON
            try:
                suggestion_json = json.loads(suggestion_text)
                logger.debug("Successfully parsed general suggestions as JSON")
                
                return {
                    "type": "general",
                    "structured_suggestion": suggestion_json
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse general suggestions as JSON, using raw text")
                return {
                    "type": "general",
                    "suggestion": suggestion_text
                }
                
        except Exception as e:
            logger.error(f"Error generating general suggestions: {e}", exc_info=True)
            return None
    
    def _extract_function_code(self, lines: List[str], start_line: int) -> str:
        """
        Extract function code from source code lines.
        
        Args:
            lines: Source code lines
            start_line: Starting line number of the function
            
        Returns:
            Function code as a string
        """
        function_lines = []
        indent_level = None
        i = start_line - 1  # Convert to 0-indexed
        
        # Get the indentation level of the function definition
        if i < len(lines):
            line = lines[i]
            indent_level = len(line) - len(line.lstrip())
            function_lines.append(line)
            i += 1
        
        # Extract the function body
        while i < len(lines):
            line = lines[i]
            if line.strip() == "":
                function_lines.append(line)
                i += 1
                continue
                
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip():
                break
                
            function_lines.append(line)
            i += 1
            
        return "\n".join(function_lines)

def generate_ai_review(code: str, file_path: str, api_key: Optional[str] = None, model: str = "gpt-4o") -> Dict[str, Any]:
    """
    Generate a comprehensive AI review of the code.
    
    This is a standalone function that can be called directly without instantiating the SuggestionGenerator class.
    
    Args:
        code: Source code to analyze
        file_path: Path to the file being analyzed
        api_key: OpenAI API key (optional, will use environment variable if not provided)
        model: OpenAI model to use (default: gpt-4o)
        
    Returns:
        Dictionary with AI review results containing suggestions and improvements
    """
    try:
        logger.info(f"Generating AI review for {file_path}")
        
        # Initialize the suggestion generator
        suggester = SuggestionGenerator(api_key=api_key, model=model)
        
        # Create a minimal analysis structure for the file
        analysis = {
            "file_path": file_path,
            "loc": len(code.splitlines()),
            "language": "python" if file_path.endswith(".py") else 
                       "javascript" if file_path.endswith(".js") else
                       "typescript" if file_path.endswith(".ts") else "unknown"
        }
        
        # Generate the AI review
        result = suggester.generate_ai_review(code, analysis)
        
        # Extract the review from the result
        if "review" in result:
            ai_review = result["review"]
            
            # Convert the AI review to a standardized format
            standardized_review = {
                "suggestions": []
            }
            
            # Extract suggestions from the AI review
            if "suggestions" in ai_review:
                for suggestion in ai_review["suggestions"]:
                    standardized_suggestion = {
                        "title": suggestion.get("title", "Suggestion"),
                        "description": suggestion.get("description", ""),
                        "severity": suggestion.get("severity", "medium"),
                        "category": suggestion.get("category", "general"),
                        "location": suggestion.get("location", ""),
                    }
                    
                    # Add code improvement if available
                    if "improvement" in suggestion:
                        standardized_suggestion["code"] = suggestion["improvement"]
                    
                    standardized_review["suggestions"].append(standardized_suggestion)
            
            # Add summary if available
            if "summary" in ai_review:
                standardized_review["summary"] = ai_review["summary"]
            
            # Add overall quality if available
            if "overall_quality" in ai_review:
                standardized_review["quality"] = ai_review["overall_quality"]
            
            return standardized_review
        else:
            # Return error information
            logger.error(f"Error in AI review: {result.get('error', 'Unknown error')}")
            return {
                "error": result.get("error", "Unknown error"),
                "suggestions": []
            }
    except Exception as e:
        logger.error(f"Error generating AI review: {e}", exc_info=True)
        return {
            "error": str(e),
            "suggestions": []
        } 