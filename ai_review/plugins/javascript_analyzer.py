"""
JavaScript language analyzer plugin for the AI code review system.
"""

import re
from typing import Dict, List, Any

from ai_review.plugin_loader import LanguageAnalyzerBase

# Define the supported file extensions
SUPPORTED_EXTENSIONS = ['.js']


class Analyzer(LanguageAnalyzerBase):
    """Analyzes JavaScript code to extract functions, classes, and complexity metrics."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a file path.
        
        Args:
            file_path: Path to the JavaScript file to analyze
        """
        super().__init__(file_path)
    
    def extract_functions(self) -> List[Dict[str, Any]]:
        """
        Extract all functions from the code.
        
        Returns:
            List of dictionaries containing function information
        """
        functions = []
        
        # Regular function declarations
        func_pattern = r'function\s+(\w+)\s*\(([^)]*)\)'
        func_matches = re.finditer(func_pattern, self.source_code)
        
        for match in func_matches:
            name = match.group(1)
            args_str = match.group(2).strip()
            args = [arg.strip() for arg in args_str.split(',')] if args_str else []
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            # Extract function body to calculate complexity
            body_start = self.source_code.find('{', match.end())
            if body_start != -1:
                # Find matching closing brace
                body_end = self._find_matching_brace(self.source_code, body_start)
                if body_end != -1:
                    body = self.source_code[body_start:body_end+1]
                    complexity = self.calculate_complexity(body)
                else:
                    complexity = 1
            else:
                complexity = 1
            
            functions.append({
                'name': name,
                'line_number': line_number,
                'args': args,
                'complexity': complexity
            })
        
        # Arrow functions with explicit names (const/let/var assignments)
        arrow_pattern = r'(const|let|var)\s+(\w+)\s*=\s*(?:\(([^)]*)\)|(\w+))\s*=>'
        arrow_matches = re.finditer(arrow_pattern, self.source_code)
        
        for match in arrow_matches:
            name = match.group(2)
            args_str = match.group(3) or match.group(4) or ''
            args = [arg.strip() for arg in args_str.split(',')] if args_str else []
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            # Extract function body to calculate complexity
            body_start = self.source_code.find('{', match.end())
            if body_start != -1:
                # Find matching closing brace
                body_end = self._find_matching_brace(self.source_code, body_start)
                if body_end != -1:
                    body = self.source_code[body_start:body_end+1]
                    complexity = self.calculate_complexity(body)
                else:
                    complexity = 1
            else:
                # Arrow function with implicit return
                complexity = 1
            
            functions.append({
                'name': name,
                'line_number': line_number,
                'args': args,
                'complexity': complexity
            })
        
        # Method definitions in objects and classes
        method_pattern = r'(\w+)\s*\(([^)]*)\)\s*{'
        method_matches = re.finditer(method_pattern, self.source_code)
        
        for match in method_matches:
            name = match.group(1)
            args_str = match.group(2).strip()
            args = [arg.strip() for arg in args_str.split(',')] if args_str else []
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            # Extract function body to calculate complexity
            body_start = self.source_code.find('{', match.end())
            if body_start != -1:
                # Find matching closing brace
                body_end = self._find_matching_brace(self.source_code, body_start)
                if body_end != -1:
                    body = self.source_code[body_start:body_end+1]
                    complexity = self.calculate_complexity(body)
                else:
                    complexity = 1
            else:
                complexity = 1
            
            # Skip constructor methods as they'll be part of classes
            if name != 'constructor':
                functions.append({
                    'name': name,
                    'line_number': line_number,
                    'args': args,
                    'complexity': complexity
                })
        
        return functions
    
    def extract_classes(self) -> List[Dict[str, Any]]:
        """
        Extract all classes from the code.
        
        Returns:
            List of dictionaries containing class information
        """
        classes = []
        
        # Class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
        class_matches = re.finditer(class_pattern, self.source_code)
        
        for match in class_matches:
            name = match.group(1)
            parent = match.group(2)
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            # Find class body
            body_start = self.source_code.find('{', match.end())
            if body_start != -1:
                # Find matching closing brace
                body_end = self._find_matching_brace(self.source_code, body_start)
                if body_end != -1:
                    body = self.source_code[body_start+1:body_end]
                    
                    # Extract methods
                    method_pattern = r'(\w+)\s*\(([^)]*)\)\s*{'
                    method_matches = re.finditer(method_pattern, body)
                    methods = [m.group(1) for m in method_matches]
                    
                    complexity = self.calculate_complexity(body)
                else:
                    methods = []
                    complexity = 1
            else:
                methods = []
                complexity = 1
            
            classes.append({
                'name': name,
                'line_number': line_number,
                'parent': parent,
                'methods': methods,
                'complexity': complexity
            })
        
        return classes
    
    def calculate_complexity(self, code_element: str) -> int:
        """
        Calculate cyclomatic complexity of a code element.
        
        Args:
            code_element: Code string to analyze
            
        Returns:
            Complexity score (higher means more complex)
        """
        complexity = 1  # Base complexity
        
        # Count control flow statements
        complexity += code_element.count('if ')
        complexity += code_element.count('else if ')
        complexity += code_element.count('for ')
        complexity += code_element.count('while ')
        complexity += code_element.count('switch ')
        complexity += code_element.count('case ')
        complexity += code_element.count('try ')
        complexity += code_element.count('catch ')
        
        # Count logical operators
        complexity += code_element.count(' && ')
        complexity += code_element.count(' || ')
        complexity += code_element.count('?')  # Ternary operator
        
        return complexity
    
    def _find_matching_brace(self, text: str, open_pos: int) -> int:
        """
        Find the position of the matching closing brace.
        
        Args:
            text: Text to search in
            open_pos: Position of the opening brace
            
        Returns:
            Position of the matching closing brace or -1 if not found
        """
        if text[open_pos] != '{':
            return -1
        
        stack = 1
        pos = open_pos + 1
        
        while pos < len(text) and stack > 0:
            if text[pos] == '{':
                stack += 1
            elif text[pos] == '}':
                stack -= 1
            pos += 1
        
        return pos - 1 if stack == 0 else -1


class Plugin:
    """Plugin class for JavaScript analyzer."""
    
    def __init__(self):
        """Initialize the plugin."""
        pass
    
    def on_analyze(self, file_path: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook called after code analysis.
        
        Args:
            file_path: Path to the analyzed file
            analysis: Analysis results
            
        Returns:
            Modified analysis results
        """
        # Add JavaScript-specific analysis if needed
        if file_path.endswith('.js'):
            analysis['language'] = 'JavaScript'
            
        return analysis 