"""
Module for applying suggested fixes to code.
"""

import os
import re
import json
import shutil
import traceback
from typing import Dict, List, Any, Optional
from openai import OpenAI

from ai_review.logger import logger


class FixApplier:
    """Applies suggested fixes to code."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the fix applier.
        
        Args:
            api_key: OpenAI API key (optional, will use environment variable if not provided)
            model: OpenAI model to use (default: gpt-3.5-turbo)
        """
        logger.debug(f"Initializing FixApplier with model: {model}")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key is missing")
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.model = model
            logger.debug("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            logger.debug(traceback.format_exc())
            raise
    
    def apply_fix(self, file_path: str, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a suggested fix to the code.
        
        Args:
            file_path: Path to the file to modify
            suggestion: Suggestion to apply
            
        Returns:
            Result of the fix application
        """
        logger.info(f"Applying fix to file: {file_path}")
        logger.debug(f"Suggestion: {json.dumps(suggestion, indent=2)}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File does not exist: {file_path}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Read the original code
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    original_code = file.read()
                logger.debug(f"Successfully read file: {file_path} ({len(original_code)} bytes)")
            except Exception as e:
                error_msg = f"Error reading file {file_path}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Generate the fixed code
            try:
                fixed_code = self._generate_fixed_code(original_code, suggestion)
                logger.debug(f"Generated fixed code ({len(fixed_code)} bytes)")
            except Exception as e:
                error_msg = f"Error generating fixed code: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {
                    "success": False,
                    "message": error_msg
                }
            
            if fixed_code == original_code:
                logger.info("No changes were made to the code")
                return {
                    "success": False,
                    "message": "No changes were made to the code"
                }
            
            # Create a backup of the original file
            backup_path = f"{file_path}.bak"
            try:
                with open(backup_path, 'w', encoding='utf-8') as file:
                    file.write(original_code)
                logger.debug(f"Created backup at: {backup_path}")
            except Exception as e:
                error_msg = f"Error creating backup file {backup_path}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Write the fixed code
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(fixed_code)
                logger.debug(f"Successfully wrote fixed code to: {file_path}")
            except Exception as e:
                error_msg = f"Error writing fixed code to {file_path}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                # Try to restore from backup
                try:
                    shutil.copy(backup_path, file_path)
                    logger.info(f"Restored original file from backup after write failure")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {str(restore_error)}")
                return {
                    "success": False,
                    "message": error_msg
                }
            
            logger.info(f"Fix applied successfully to {file_path}")
            return {
                "success": True,
                "message": f"Fix applied successfully. Original code backed up to {backup_path}",
                "backup_path": backup_path
            }
        except Exception as e:
            error_msg = f"Error applying fix: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg
            }
    
    def apply_ai_fixes(self, file_path: str, ai_review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply fixes based on AI review suggestions.
        
        Args:
            file_path: Path to the file to modify
            ai_review: AI review containing suggestions
            
        Returns:
            Result of the fix application
        """
        logger.info(f"Applying AI fixes to file: {file_path}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File does not exist: {file_path}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Create a backup of the original file
            backup_path = f"{file_path}.bak"
            try:
                shutil.copy(file_path, backup_path)
                logger.debug(f"Created backup at: {backup_path}")
            except Exception as e:
                error_msg = f"Error creating backup file {backup_path}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Read the original code
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    original_code = file.read()
                    original_lines = original_code.splitlines()
                logger.debug(f"Successfully read file: {file_path} ({len(original_lines)} lines)")
            except Exception as e:
                error_msg = f"Error reading file {file_path}: {str(e)}"
                logger.error(error_msg)
                logger.debug(traceback.format_exc())
                return {
                    "success": False,
                    "message": error_msg
                }
            
            # Get suggestions from AI review
            suggestions = ai_review.get("suggestions", [])
            if not suggestions:
                logger.warning("No suggestions found in AI review")
                return {
                    "success": False,
                    "message": "No suggestions found in AI review"
                }
            
            # Apply fixes based on suggestions
            modified_code = original_code
            applied_fixes = []
            
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Create fix log file
            fix_log_path = os.path.join(logs_dir, "fix_log.json")
            
            # Check if fix log file exists, if not create it with an empty array
            if not os.path.exists(fix_log_path):
                with open(fix_log_path, "w") as log_file:
                    log_file.write("[\n]\n")
            
            # Process each suggestion
            for suggestion in suggestions:
                title = suggestion.get("title", "")
                location = suggestion.get("location", "")
                improvement = suggestion.get("improvement", "")
                severity = suggestion.get("severity", "low")
                
                if not improvement or not location:
                    continue
                
                # Create a fix log entry
                fix_log_entry = {
                    "timestamp": self._get_timestamp(),
                    "file": file_path,
                    "title": title,
                    "location": location,
                    "severity": severity,
                    "before": original_code,
                    "suggested_fix": improvement
                }
                
                # Log the fix before applying it
                try:
                    # Read the existing log file
                    with open(fix_log_path, "r") as log_file:
                        content = log_file.read()
                    
                    # Remove the closing bracket
                    if content.strip().endswith("]"):
                        content = content.strip()[:-1]
                        if content.strip().endswith(","):
                            content = content.strip()
                        else:
                            content = content.strip() + ","
                    
                    # Append the new entry
                    with open(fix_log_path, "w") as log_file:
                        log_file.write(content + "\n")
                        json.dump(fix_log_entry, log_file, indent=2)
                        log_file.write("\n]")
                    
                    logger.info(f"Logged fix for {file_path}: {title}")
                except Exception as e:
                    logger.error(f"Error logging fix: {str(e)}")
                
                # Ask for confirmation before applying the fix
                print("\n" + "=" * 80)
                print(f"AI-suggested fix: {title}")
                print(f"Location: {location}")
                print(f"Severity: {severity}")
                print("-" * 80)
                print("Suggested improvement:")
                print("-" * 80)
                print(improvement)
                print("=" * 80)
                
                confirm = input(f"Apply this fix to {file_path}? (Y/N): ")
                if confirm.lower() != "y":
                    logger.info(f"Skipping fix: {title}")
                    print(f"Skipping fix: {title}")
                    continue
                
                # Try to extract line numbers or function names from location
                line_numbers = self._extract_line_numbers(location)
                function_name = self._extract_function_name(location)
                
                # Apply the fix
                if line_numbers:
                    # Apply fix to specific lines
                    modified_code = self._apply_line_fix(modified_code, line_numbers, improvement)
                    applied_fixes.append({
                        "title": title,
                        "location": location,
                        "severity": severity
                    })
                elif function_name:
                    # Apply fix to a function
                    modified_code = self._apply_function_fix(modified_code, function_name, improvement)
                    applied_fixes.append({
                        "title": title,
                        "location": location,
                        "severity": severity
                    })
            
            if modified_code == original_code:
                logger.info("No changes were made to the code")
                return {
                    "success": False,
                    "message": "No changes were made to the code"
                }
            
            # Write the modified code
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(modified_code)
            
            # Update the fix log with the final code
            final_log_entry = {
                "timestamp": self._get_timestamp(),
                "file": file_path,
                "applied_fixes": applied_fixes,
                "before": original_code,
                "after": modified_code
            }
            
            try:
                # Read the existing log file
                with open(fix_log_path, "r") as log_file:
                    content = log_file.read()
                
                # Remove the closing bracket
                if content.strip().endswith("]"):
                    content = content.strip()[:-1]
                    if content.strip().endswith(","):
                        content = content.strip()
                    else:
                        content = content.strip() + ","
                
                # Append the new entry
                with open(fix_log_path, "w") as log_file:
                    log_file.write(content + "\n")
                    json.dump(final_log_entry, log_file, indent=2)
                    log_file.write("\n]")
                
                logger.info(f"Logged final changes for {file_path}")
            except Exception as e:
                logger.error(f"Error logging final changes: {str(e)}")
            
            logger.info(f"Applied {len(applied_fixes)} fixes to {file_path}")
            return {
                "success": True,
                "message": f"Applied {len(applied_fixes)} fixes. Original code backed up to {backup_path}",
                "backup_path": backup_path,
                "applied_fixes": applied_fixes
            }
        except Exception as e:
            error_msg = f"Error applying AI fixes: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return {
                "success": False,
                "message": error_msg
            }
    
    def _extract_line_numbers(self, location: str) -> List[int]:
        """
        Extract line numbers from a location string.
        
        Args:
            location: Location string (e.g., "lines 10-15" or "line 20")
            
        Returns:
            List of line numbers
        """
        line_numbers = []
        
        # Match patterns like "line 10" or "lines 10-15"
        single_line_match = re.search(r'line\s+(\d+)', location, re.IGNORECASE)
        range_match = re.search(r'lines\s+(\d+)-(\d+)', location, re.IGNORECASE)
        
        if single_line_match:
            line_numbers.append(int(single_line_match.group(1)))
        elif range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            line_numbers.extend(range(start, end + 1))
        
        return line_numbers
    
    def _extract_function_name(self, location: str) -> Optional[str]:
        """
        Extract function name from a location string.
        
        Args:
            location: Location string (e.g., "function very_complex_function")
            
        Returns:
            Function name or None if not found
        """
        function_match = re.search(r'function\s+([a-zA-Z0-9_]+)', location, re.IGNORECASE)
        if function_match:
            return function_match.group(1)
        return None
    
    def _apply_line_fix(self, code: str, line_numbers: List[int], improvement: str) -> str:
        """
        Apply a fix to specific lines in the code.
        
        Args:
            code: Original code
            line_numbers: Line numbers to modify
            improvement: Suggested improvement
            
        Returns:
            Modified code
        """
        lines = code.splitlines()
        
        # Extract code from the improvement
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', improvement, re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r'```\s*(.*?)\s*```', improvement, re.DOTALL)
        
        if code_blocks:
            new_code = code_blocks[0].strip()
            new_lines = new_code.splitlines()
            
            # Replace the lines
            if len(line_numbers) == 1 and len(new_lines) == 1:
                # Single line replacement
                line_idx = line_numbers[0] - 1
                if 0 <= line_idx < len(lines):
                    lines[line_idx] = new_lines[0]
            elif len(line_numbers) > 0 and len(new_lines) > 0:
                # Multi-line replacement
                start_idx = line_numbers[0] - 1
                end_idx = line_numbers[-1] - 1 if len(line_numbers) > 1 else start_idx
                
                if 0 <= start_idx < len(lines) and 0 <= end_idx < len(lines):
                    # Replace the range with new lines
                    lines = lines[:start_idx] + new_lines + lines[end_idx + 1:]
        
        return "\n".join(lines)
    
    def _apply_function_fix(self, code: str, function_name: str, improvement: str) -> str:
        """
        Apply a fix to a function in the code.
        
        Args:
            code: Original code
            function_name: Name of the function to modify
            improvement: Suggested improvement
            
        Returns:
            Modified code
        """
        # Find the function in the code
        function_pattern = r'def\s+' + re.escape(function_name) + r'\s*\('
        match = re.search(function_pattern, code)
        
        if not match:
            return code
        
        # Extract code from the improvement
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', improvement, re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r'```\s*(.*?)\s*```', improvement, re.DOTALL)
        
        if not code_blocks:
            return code
        
        new_function = code_blocks[0].strip()
        
        # Find the line number of the function
        lines = code.splitlines()
        line_number = 0
        for i, line in enumerate(lines):
            if re.search(function_pattern, line):
                line_number = i + 1
                break
        
        if line_number == 0:
            return code
        
        # Replace the function
        return self._replace_function_in_code(code, function_name, line_number, new_function)
    
    def _generate_fixed_code(self, original_code: str, suggestion: Dict[str, Any]) -> str:
        """
        Generate fixed code based on the suggestion.
        
        Args:
            original_code: Original source code
            suggestion: Suggestion to apply
            
        Returns:
            Fixed code
        """
        suggestion_type = suggestion.get("type", "")
        
        if suggestion_type == "complex_function":
            return self._fix_complex_function(original_code, suggestion)
        elif suggestion_type == "general":
            return self._apply_general_fix(original_code, suggestion)
        else:
            # Unknown suggestion type
            return original_code
    
    def _fix_complex_function(self, original_code: str, suggestion: Dict[str, Any]) -> str:
        """
        Fix a complex function based on the suggestion.
        
        Args:
            original_code: Original source code
            suggestion: Suggestion for the complex function
            
        Returns:
            Fixed code
        """
        function_name = suggestion.get("function_name", "")
        line_number = suggestion.get("line_number", 0)
        suggestion_text = suggestion.get("suggestion", "")
        
        if not function_name or not line_number:
            return original_code
        
        # Extract the function code
        lines = original_code.splitlines()
        function_code = self._extract_function_code(lines, line_number)
        
        if not function_code:
            return original_code
        
        # Generate the fixed function using OpenAI
        system_prompt = """
        You are an expert code refactorer. Your task is to rewrite a Python function based on the provided suggestions.
        Return ONLY the improved function code, nothing else. Do not include any explanations or markdown formatting.
        """
        
        user_prompt = f"""
        Original function:
        ```python
        {function_code}
        ```
        
        Suggestion:
        {suggestion_text}
        
        Rewrite the function with the suggested improvements. Return ONLY the improved function code, nothing else.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            fixed_function = response.choices[0].message.content.strip()
            
            # Remove any markdown code blocks
            fixed_function = re.sub(r'```python\s*', '', fixed_function)
            fixed_function = re.sub(r'```\s*', '', fixed_function)
            
            # Replace the original function with the fixed one
            return self._replace_function_in_code(original_code, function_name, line_number, fixed_function)
        except Exception as e:
            print(f"Error generating fixed function: {e}")
            return original_code
    
    def _apply_general_fix(self, original_code: str, suggestion: Dict[str, Any]) -> str:
        """
        Apply general fixes to the code.
        
        Args:
            original_code: Original source code
            suggestion: General suggestion
            
        Returns:
            Fixed code
        """
        suggestion_text = suggestion.get("suggestion", "")
        
        # Generate the fixed code using OpenAI
        system_prompt = """
        You are an expert code refactorer. Your task is to rewrite Python code based on the provided suggestions.
        Return ONLY the improved code, nothing else. Do not include any explanations or markdown formatting.
        """
        
        user_prompt = f"""
        Original code:
        ```python
        {original_code}
        ```
        
        Suggestion:
        {suggestion_text}
        
        Rewrite the code with the suggested improvements. Return ONLY the improved code, nothing else.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            fixed_code = response.choices[0].message.content.strip()
            
            # Remove any markdown code blocks
            fixed_code = re.sub(r'```python\s*', '', fixed_code)
            fixed_code = re.sub(r'```\s*', '', fixed_code)
            
            return fixed_code
        except Exception as e:
            print(f"Error generating fixed code: {e}")
            return original_code
    
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
    
    def _replace_function_in_code(self, code: str, function_name: str, line_number: int, new_function: str) -> str:
        """
        Replace a function in the code with a new implementation.
        
        Args:
            code: Original source code
            function_name: Name of the function to replace
            line_number: Line number where the function starts
            new_function: New function implementation
            
        Returns:
            Updated code
        """
        lines = code.splitlines()
        
        # Find the function boundaries
        start_idx = line_number - 1  # Convert to 0-indexed
        end_idx = start_idx
        
        # Get the indentation level of the function definition
        if start_idx < len(lines):
            line = lines[start_idx]
            indent_level = len(line) - len(line.lstrip())
            
            # Find the end of the function
            i = start_idx + 1
            while i < len(lines):
                line = lines[i]
                if line.strip() == "":
                    i += 1
                    continue
                    
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    break
                    
                i += 1
                
            end_idx = i - 1
        
        # Replace the function
        new_lines = lines[:start_idx] + new_function.splitlines() + lines[end_idx+1:]
        return "\n".join(new_lines)

    def _get_timestamp(self):
        """Get the current timestamp as a string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CodeFixer:
    """Applies AI-suggested fixes to code."""
    
    def __init__(self, file_path: str):
        """
        Initialize the code fixer.
        
        Args:
            file_path: Path to the file to modify
        """
        self.file_path = file_path
    
    def apply_fixes(self, suggestions: Dict[str, Any]) -> str:
        """
        Apply fixes based on AI suggestions.
        
        Args:
            suggestions: AI-generated suggestions
            
        Returns:
            Message indicating the result
        """
        try:
            # Create a backup of the original file
            backup_path = f"{self.file_path}.bak"
            shutil.copy(self.file_path, backup_path)
            
            # Read the original code
            with open(self.file_path, "r", encoding="utf-8") as f:
                code = f.readlines()
            
            # Track changes
            changes_made = False
            
            # Apply fixes based on AI suggestions
            if "suggestions" in suggestions:
                for suggestion in suggestions["suggestions"]:
                    location = suggestion.get("location", "")
                    improvement = suggestion.get("improvement", "")
                    
                    # Try to extract line numbers
                    line_match = re.search(r'line\s+(\d+)', location, re.IGNORECASE)
                    range_match = re.search(r'lines\s+(\d+)-(\d+)', location, re.IGNORECASE)
                    
                    if line_match and improvement:
                        line_number = int(line_match.group(1))
                        if 0 < line_number <= len(code):
                            # Extract code from the improvement
                            code_blocks = re.findall(r'```python\s*(.*?)\s*```', improvement, re.DOTALL)
                            if not code_blocks:
                                code_blocks = re.findall(r'```\s*(.*?)\s*```', improvement, re.DOTALL)
                            
                            if code_blocks:
                                new_code = code_blocks[0].strip()
                                code[line_number - 1] = new_code + "\n"
                                changes_made = True
                    
                    elif range_match and improvement:
                        start_line = int(range_match.group(1))
                        end_line = int(range_match.group(2))
                        
                        if 0 < start_line <= len(code) and 0 < end_line <= len(code):
                            # Extract code from the improvement
                            code_blocks = re.findall(r'```python\s*(.*?)\s*```', improvement, re.DOTALL)
                            if not code_blocks:
                                code_blocks = re.findall(r'```\s*(.*?)\s*```', improvement, re.DOTALL)
                            
                            if code_blocks:
                                new_code = code_blocks[0].strip()
                                new_lines = new_code.splitlines()
                                
                                # Replace the range with new lines
                                code = code[:start_line - 1] + [line + "\n" for line in new_lines] + code[end_line:]
                                changes_made = True
            
            # Write the updated code back if changes were made
            if changes_made:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.writelines(code)
                return f"Fixes applied successfully! Backup saved at {backup_path}"
            else:
                return "No fixes were applied. No changes were needed or suggestions didn't contain applicable fixes."
        
        except Exception as e:
            return f"Error applying fixes: {str(e)}" 