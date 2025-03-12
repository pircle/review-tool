"""
Code analyzer module for extracting functions, classes, and complexity metrics.
"""

import ast
import os
import pathlib
import traceback
import re
from typing import Dict, List, Any, Optional, Type

from ai_review.plugin_loader import PluginLoader, LanguageAnalyzerBase
from ai_review.logger import logger
from ai_review.config_manager import config_manager


def analyze_typescript_state_management(file_content: str) -> Dict[str, Any]:
    """
    Analyze TypeScript files for Zustand state management patterns.
    
    Args:
        file_content: Content of the TypeScript file
        
    Returns:
        Dictionary with analysis results
    """
    result = {
        "zustand_store_detected": False,
        "issues": [],
        "recommendations": []
    }
    
    # Check if file contains Zustand imports
    if "zustand" in file_content:
        result["zustand_store_detected"] = True
        result["recommendations"].append("⚠️ Zustand store detected. Ensure state updates are optimized.")
        
        # Check for create store pattern
        if "create(" in file_content or "createStore" in file_content:
            result["recommendations"].append("Ensure store creation is done outside of components to prevent recreation.")
            
            # Check for potential issues
            if "setState" in file_content and "useEffect" in file_content:
                result["issues"].append("Potential issue: setState inside useEffect may cause unnecessary re-renders.")
            
            # Check for selector usage
            if not re.search(r'useStore\(\s*state\s*=>\s*state\.', file_content):
                result["issues"].append("Consider using selectors (state => state.property) to prevent unnecessary re-renders.")
            
            # Check for middleware usage
            if "devtools" not in file_content and "process.env.NODE_ENV !== 'production'" in file_content:
                result["recommendations"].append("Consider using devtools middleware for better debugging in development.")
        
        # Check for inefficient state updates
        if "useStore(" in file_content and "set(" in file_content:
            result["issues"].append("⚠️ Check if set() calls are causing unnecessary re-renders. Consider using immer middleware for immutable updates.")
        
        # Check for deep selector patterns
        deep_selector_pattern = re.search(r'useStore\(\s*state\s*=>\s*state\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+', file_content)
        if deep_selector_pattern:
            result["issues"].append("Deep selectors detected. Consider using shallow selectors with equality functions to prevent unnecessary re-renders.")
        
        # Check for multiple store instances
        if file_content.count("create(") > 1 or file_content.count("createStore") > 1:
            result["issues"].append("Multiple store instances detected. Consider using a single store with slices for better state management.")
        
        # Check for store reset patterns
        if "getState()" in file_content and "setState" in file_content:
            result["recommendations"].append("Store reset pattern detected. Ensure you're not resetting the entire store unnecessarily.")
        
        # Check for subscription usage
        if "subscribe" in file_content:
            result["recommendations"].append("Manual subscriptions detected. Prefer using hooks (useStore) over manual subscriptions.")
    
    # Check for React hooks with state management
    if "useState" in file_content and "useEffect" in file_content:
        # Check for potential dependency array issues
        if re.search(r'useEffect\(\s*\(\)\s*=>\s*{[^}]+}\s*,\s*\[\s*\]\s*\)', file_content):
            result["issues"].append("Empty dependency array in useEffect with state updates may cause stale closures.")
        
        # Check for missing dependencies
        if re.search(r'useEffect\(\s*\(\)\s*=>\s*{[^}]+setState[^}]+}\s*,\s*\[[^\]]*\]\s*\)', file_content):
            result["issues"].append("Check useEffect dependency arrays for completeness to avoid stale state updates.")
        
        # Check for excessive re-renders
        if file_content.count("useState") > 5:
            result["recommendations"].append("Multiple useState hooks detected. Consider consolidating state or using a reducer for complex state logic.")
    
    return result


def analyze_typescript_types(file_content: str) -> Dict[str, Any]:
    """
    Analyze TypeScript files for type definitions and potential issues.
    
    Args:
        file_content: Content of the TypeScript file
        
    Returns:
        Dictionary with analysis results
    """
    result = {
        "interfaces_detected": False,
        "types_detected": False,
        "issues": [],
        "recommendations": []
    }
    
    # Check for interface definitions
    interfaces = re.findall(r'interface\s+(\w+)', file_content)
    if interfaces:
        result["interfaces_detected"] = True
        result["interfaces"] = interfaces
        
        # Check for potential issues with interfaces
        if "any" in file_content:
            result["issues"].append("Usage of 'any' type detected. Consider using more specific types.")
        
        # Check for index signatures
        if re.search(r'\[\s*key\s*:\s*string\s*\]', file_content):
            result["recommendations"].append("Index signatures detected. Consider using Record<K, V> for better type safety.")
        
        # Check for large interfaces
        interface_blocks = re.findall(r'interface\s+\w+\s*{[^}]*}', file_content)
        for block in interface_blocks:
            if block.count('\n') > 20:
                result["issues"].append("⚠️ Large interface detected. Consider breaking down large interfaces into smaller, more focused ones.")
        
        # Check for interface extension
        if re.search(r'interface\s+\w+\s+extends', file_content):
            result["recommendations"].append("Interface extension detected. Ensure you're not creating deep inheritance hierarchies.")
    
    # Check for type definitions
    types = re.findall(r'type\s+(\w+)', file_content)
    if types:
        result["types_detected"] = True
        result["types"] = types
        
        # Check for union types
        if re.search(r'type\s+\w+\s*=\s*[^|]+\|[^|]+', file_content):
            result["recommendations"].append("Union types detected. Ensure exhaustive checks when using them.")
        
        # Check for large or complex types
        if "type" in file_content and "{" in file_content and len(file_content.split("\n")) > 30:
            result["issues"].append("⚠️ Large TypeScript type detected. Consider modularizing complex types.")
        
        # Check for complex mapped types
        if "keyof" in file_content and "extends" in file_content:
            result["recommendations"].append("Complex mapped types detected. Consider simplifying for better readability.")
        
        # Check for conditional types
        if re.search(r'extends\s+.*\s+\?\s+.*\s+:', file_content):
            result["issues"].append("Conditional types detected. These can be hard to understand - consider simplifying or adding documentation.")
    
    # Check for React component types
    if "React.FC" in file_content or "FunctionComponent" in file_content:
        result["recommendations"].append("Consider using function declarations with explicit return types instead of React.FC.")
    
    # Check for prop types
    if "Props" in file_content:
        if not re.search(r'(interface|type)\s+\w*Props', file_content):
            result["issues"].append("Props usage detected but no Props interface/type defined.")
        
        # Check for optional props
        if re.search(r'(\w+)\?:', file_content):
            result["recommendations"].append("Optional props detected. Consider providing default values for optional props.")
    
    # Check for generic types
    if re.search(r'<[A-Z][^>]*>', file_content):
        result["recommendations"].append("Generic types detected. Ensure they have appropriate constraints.")
    
    # Check for type assertions
    if "as " in file_content:
        result["issues"].append("Type assertions (using 'as') detected. These bypass TypeScript's type checking - use with caution.")
    
    # Check for non-null assertions
    if "!" in file_content:
        result["issues"].append("Non-null assertions (!) detected. These can lead to runtime errors - consider safer alternatives.")
    
    return result


class CodeAnalyzer:
    """Analyzes code to extract functions, classes, and complexity metrics."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a file path.
        
        Args:
            file_path: Path to the file to analyze
        """
        self.file_path = file_path
        self.plugin_loader = PluginLoader()
        
        try:
            logger.debug(f"Loading plugins for file: {file_path}")
            self.plugin_loader.load_all_plugins()
            logger.debug(f"Loaded {len(self.plugin_loader.language_analyzers)} language analyzers")
        except Exception as e:
            logger.error(f"Error loading plugins: {str(e)}")
            logger.debug(traceback.format_exc())
        
    def get_analyzer_for_file(self) -> Optional[Type[LanguageAnalyzerBase]]:
        """
        Get the appropriate analyzer class for the file.
        
        Returns:
            Analyzer class or None if not found
        """
        try:
            file_extension = pathlib.Path(self.file_path).suffix.lower()
            analyzer_class = self.plugin_loader.get_analyzer_for_extension(file_extension)
            
            if analyzer_class:
                logger.debug(f"Found analyzer for extension {file_extension}: {analyzer_class.__name__}")
            else:
                logger.warning(f"No analyzer found for extension: {file_extension}")
                
            return analyzer_class
        except Exception as e:
            logger.error(f"Error getting analyzer for file: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform full analysis of the code.
        
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing file: {self.file_path}")
        
        try:
            # Get the appropriate analyzer for the file
            analyzer_class = self.get_analyzer_for_file()
            
            if analyzer_class:
                # Use the language-specific analyzer
                analyzer = analyzer_class(self.file_path)
                analysis = analyzer.analyze()
                
                # Add language information based on file extension
                file_extension = pathlib.Path(self.file_path).suffix.lower()
                if file_extension == '.py':
                    analysis['language'] = 'Python'
                elif file_extension == '.js':
                    analysis['language'] = 'JavaScript'
                elif file_extension in ['.ts', '.tsx']:
                    analysis['language'] = 'TypeScript'
                    
                    # Add TypeScript-specific analysis
                    try:
                        with open(self.file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        # Analyze TypeScript state management
                        state_analysis = analyze_typescript_state_management(file_content)
                        if state_analysis["zustand_store_detected"]:
                            analysis['zustand_analysis'] = state_analysis
                            logger.info(f"Zustand state management detected in {self.file_path}")
                            
                            # Add issues and recommendations to the main analysis
                            if "issues" not in analysis:
                                analysis["issues"] = []
                            if "recommendations" not in analysis:
                                analysis["recommendations"] = []
                            
                            analysis["issues"].extend(state_analysis["issues"])
                            analysis["recommendations"].extend(state_analysis["recommendations"])
                        
                        # Analyze TypeScript types
                        types_analysis = analyze_typescript_types(file_content)
                        if types_analysis["interfaces_detected"] or types_analysis["types_detected"]:
                            analysis['typescript_types_analysis'] = types_analysis
                            logger.info(f"TypeScript types detected in {self.file_path}")
                            
                            # Add issues and recommendations to the main analysis
                            if "issues" not in analysis:
                                analysis["issues"] = []
                            if "recommendations" not in analysis:
                                analysis["recommendations"] = []
                            
                            analysis["issues"].extend(types_analysis["issues"])
                            analysis["recommendations"].extend(types_analysis["recommendations"])
                    except Exception as e:
                        logger.error(f"Error analyzing TypeScript file: {str(e)}")
                        logger.debug(traceback.format_exc())
                else:
                    analysis['language'] = 'Unknown'
                
                # Log analysis results
                logger.info(f"Analysis complete: {len(analysis.get('functions', []))} functions, {len(analysis.get('classes', []))} classes")
                logger.debug(f"Analysis details: {analysis}")
                
                # Call plugins' on_analyze hooks
                try:
                    logger.debug("Calling on_analyze hooks")
                    self.plugin_loader.call_hook('on_analyze', self.file_path, analysis)
                except Exception as e:
                    logger.error(f"Error calling on_analyze hooks: {str(e)}")
                    logger.debug(traceback.format_exc())
                
                return analysis
            else:
                # Fallback to basic analysis for unsupported file types
                logger.warning(f"Using fallback analysis for unsupported file type: {self.file_path}")
                return {
                    "file_path": self.file_path,
                    "language": "Unsupported",
                    "functions": [],
                    "classes": [],
                    "loc": self._count_lines(),
                    "error": "Unsupported file type"
                }
        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            logger.debug(traceback.format_exc())
            return {
                "file_path": self.file_path,
                "language": "Error",
                "functions": [],
                "classes": [],
                "loc": self._count_lines(),
                "error": str(e)
            }
    
    def _count_lines(self) -> int:
        """
        Count the number of lines in the file.
        
        Returns:
            Number of lines
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                return len(file.readlines())
        except Exception as e:
            logger.error(f"Error counting lines in file: {str(e)}")
            logger.debug(traceback.format_exc())
            return 0


def analyze_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a single file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Analysis results
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return {"error": f"File does not exist: {file_path}"}
            
        if not os.path.isfile(file_path):
            logger.error(f"Path is not a file: {file_path}")
            return {"error": f"Path is not a file: {file_path}"}
            
        analyzer = CodeAnalyzer(file_path)
        return analyzer.analyze()
    except Exception as e:
        logger.error(f"Error analyzing file {file_path}: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            "file_path": file_path,
            "error": str(e)
        }


def analyze_directory(directory_path: str) -> List[Dict[str, Any]]:
    """
    Analyze all supported files in a directory.
    
    Args:
        directory_path (str): Path to the directory to analyze
        
    Returns:
        list: List of analysis results for each file
    """
    try:
        if not os.path.exists(directory_path):
            logger.error(f"Directory does not exist: {directory_path}")
            return []
        
        if not os.path.isdir(directory_path):
            logger.error(f"Path is not a directory: {directory_path}")
            return []
        
        plugin_loader = PluginLoader()
        supported_extensions = plugin_loader.get_supported_extensions()
        
        logger.info(f"Analyzing directory: {directory_path}")
        logger.debug(f"Supported extensions: {supported_extensions}")
        
        results = []
        file_count = 0
        skipped_count = 0
        excluded_dirs = set()
        
        # Check for required directories
        required_dirs = [
            "src", "components", "pages", "backend", "server", 
            "lib", "config", "tests"
        ]
        
        found_required_dirs = []
        for required_dir in required_dirs:
            required_path = os.path.join(directory_path, required_dir)
            if os.path.exists(required_path) and os.path.isdir(required_path):
                found_required_dirs.append(required_dir)
        
        if not found_required_dirs:
            logger.warning(f"No standard project directories found in {directory_path}. "
                          f"Expected at least one of: {', '.join(required_dirs)}")
        else:
            logger.info(f"Found standard project directories: {', '.join(found_required_dirs)}")
        
        for root, dirs, files in os.walk(directory_path):
            # Filter out directories based on configuration
            original_dirs = dirs.copy()
            dirs[:] = [d for d in dirs if not config_manager.should_exclude_path(os.path.join(root, d))]
            
            # Track excluded directories
            for d in original_dirs:
                if d not in dirs:
                    excluded_dirs.add(d)
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file should be excluded based on configuration
                if config_manager.should_exclude_path(file_path):
                    logger.debug(f"Skipping file (excluded by config): {file_path}")
                    skipped_count += 1
                    continue
                
                file_extension = pathlib.Path(file).suffix.lower()
                if file_extension in supported_extensions:
                    logger.debug(f"Found supported file: {file_path}")
                    file_count += 1
                    try:
                        results.append(analyze_file(file_path))
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {str(e)}")
                        logger.debug(traceback.format_exc())
        
        # Log excluded directories
        if excluded_dirs:
            logger.info(f"Excluded directories: {', '.join(sorted(excluded_dirs))}")
        
        logger.info(f"Analyzed {file_count} files in directory: {directory_path}")
        logger.info(f"Skipped {skipped_count} files based on configuration filters")
        
        # Return analysis results along with metadata
        return results
    except Exception as e:
        logger.error(f"Error analyzing directory {directory_path}: {str(e)}")
        logger.debug(traceback.format_exc())
        return [] 