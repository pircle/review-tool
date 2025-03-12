"""
Python language analyzer plugin for the AI code review system.
"""

import ast
from typing import Dict, List, Any

from ai_review.plugin_loader import LanguageAnalyzerBase

# Define the supported file extensions
SUPPORTED_EXTENSIONS = ['.py']


class Analyzer(LanguageAnalyzerBase):
    """Analyzes Python code to extract functions, classes, and complexity metrics."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a file path.
        
        Args:
            file_path: Path to the Python file to analyze
        """
        super().__init__(file_path)
        self.ast_tree = None
        
    def load_file(self) -> bool:
        """
        Load the source code from the file and parse the AST.
        
        Returns:
            bool: True if file was loaded successfully, False otherwise
        """
        if super().load_file():
            try:
                self.ast_tree = ast.parse(self.source_code)
                return True
            except SyntaxError as e:
                print(f"Syntax error in Python file: {e}")
                return False
        return False
    
    def extract_functions(self) -> List[Dict[str, Any]]:
        """
        Extract all functions from the code.
        
        Returns:
            List of dictionaries containing function information
        """
        functions = []
        
        if not self.ast_tree:
            return functions
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'args': [arg.arg for arg in node.args.args],
                    'complexity': self.calculate_complexity(node)
                }
                functions.append(func_info)
                
        return functions
    
    def extract_classes(self) -> List[Dict[str, Any]]:
        """
        Extract all classes from the code.
        
        Returns:
            List of dictionaries containing class information
        """
        classes = []
        
        if not self.ast_tree:
            return classes
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                
                class_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'methods': methods,
                    'complexity': self.calculate_complexity(node)
                }
                classes.append(class_info)
                
        return classes
    
    def calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity of a node.
        
        Args:
            node: AST node to analyze
            
        Returns:
            Complexity score (higher means more complex)
        """
        complexity = 1  # Base complexity
        
        for child_node in ast.walk(node):
            # Increase complexity for control flow statements
            if isinstance(child_node, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child_node, ast.BoolOp):
                # Count boolean operations (and, or)
                complexity += len(child_node.values) - 1
                
        return complexity


class Plugin:
    """Plugin class for Python analyzer."""
    
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
        # Add Python-specific analysis if needed
        if file_path.endswith('.py'):
            analysis['language'] = 'Python'
            
        return analysis 