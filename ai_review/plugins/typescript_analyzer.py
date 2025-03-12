"""
TypeScript language analyzer plugin for the AI code review system.
"""

import re
from typing import Dict, List, Any

from ai_review.plugins.javascript_analyzer import Analyzer as JavaScriptAnalyzer

# Define the supported file extensions
SUPPORTED_EXTENSIONS = ['.ts', '.tsx']


class Analyzer(JavaScriptAnalyzer):
    """Analyzes TypeScript code to extract functions, classes, and complexity metrics."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a file path.
        
        Args:
            file_path: Path to the TypeScript file to analyze
        """
        super().__init__(file_path)
    
    def extract_functions(self) -> List[Dict[str, Any]]:
        """
        Extract all functions from the code.
        
        Returns:
            List of dictionaries containing function information
        """
        # First get all JavaScript-style functions
        functions = super().extract_functions()
        
        # Add TypeScript-specific function patterns
        # Function with type annotations
        ts_func_pattern = r'function\s+(\w+)\s*<([^>]*)>?\s*\(([^)]*)\)\s*:\s*([^{]*)'
        ts_func_matches = re.finditer(ts_func_pattern, self.source_code)
        
        for match in ts_func_matches:
            name = match.group(1)
            type_params = match.group(2).strip() if match.group(2) else ""
            args_str = match.group(3).strip()
            return_type = match.group(4).strip()
            
            # Skip if this function was already found
            if any(f['name'] == name for f in functions):
                continue
                
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
            
            # Parse arguments with type annotations
            args = []
            if args_str:
                arg_pattern = r'(\w+)\s*(?::\s*([^,]*))?'
                arg_matches = re.finditer(arg_pattern, args_str)
                args = [m.group(1) for m in arg_matches]
            
            functions.append({
                'name': name,
                'line_number': line_number,
                'args': args,
                'type_params': type_params,
                'return_type': return_type,
                'complexity': complexity
            })
        
        return functions
    
    def extract_classes(self) -> List[Dict[str, Any]]:
        """
        Extract all classes from the code.
        
        Returns:
            List of dictionaries containing class information
        """
        # First get all JavaScript-style classes
        classes = super().extract_classes()
        
        # Add TypeScript-specific class patterns
        # Interface declarations
        interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+([^{]*))?'
        interface_matches = re.finditer(interface_pattern, self.source_code)
        
        for match in interface_matches:
            name = match.group(1)
            extends = match.group(2).strip() if match.group(2) else None
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            # Find interface body
            body_start = self.source_code.find('{', match.end())
            if body_start != -1:
                # Find matching closing brace
                body_end = self._find_matching_brace(self.source_code, body_start)
                if body_end != -1:
                    body = self.source_code[body_start+1:body_end]
                    
                    # Extract methods (function signatures)
                    method_pattern = r'(\w+)\s*(?:\([^)]*\))?\s*:\s*[^;]*;'
                    method_matches = re.finditer(method_pattern, body)
                    methods = [m.group(1) for m in method_matches]
                    
                    complexity = 1  # Interfaces don't have implementation complexity
                else:
                    methods = []
                    complexity = 1
            else:
                methods = []
                complexity = 1
            
            classes.append({
                'name': name,
                'line_number': line_number,
                'type': 'interface',
                'extends': extends,
                'methods': methods,
                'complexity': complexity
            })
        
        # Type declarations
        type_pattern = r'type\s+(\w+)(?:<[^>]*>)?\s*='
        type_matches = re.finditer(type_pattern, self.source_code)
        
        for match in type_matches:
            name = match.group(1)
            
            # Find the line number
            line_number = self.source_code[:match.start()].count('\n') + 1
            
            classes.append({
                'name': name,
                'line_number': line_number,
                'type': 'type',
                'methods': [],
                'complexity': 1
            })
        
        return classes


class Plugin:
    """Plugin class for TypeScript analyzer."""
    
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
        # Add TypeScript-specific analysis if needed
        if file_path.endswith(('.ts', '.tsx')):
            analysis['language'] = 'TypeScript'
            
        return analysis 