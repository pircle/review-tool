"""
Module for loading and managing plugins for the AI code review system.
"""

import os
import importlib.util
import inspect
from typing import Dict, List, Any, Callable, Optional, Type


class PluginLoader:
    """Loads and manages plugins for the AI code review system."""
    
    def __init__(self, plugins_dir: Optional[str] = None):
        """
        Initialize the plugin loader.
        
        Args:
            plugins_dir: Directory containing plugins (optional)
        """
        self.plugins_dir = plugins_dir or os.path.join(os.path.dirname(__file__), "plugins")
        self.plugins: Dict[str, Any] = {}
        self.language_analyzers: Dict[str, Type] = {}
        
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugins directory.
        
        Returns:
            List of plugin names
        """
        plugin_files = []
        
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            return plugin_files
        
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_files.append(filename[:-3])  # Remove .py extension
                
        return plugin_files
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            True if plugin was loaded successfully, False otherwise
        """
        if plugin_name in self.plugins:
            # Plugin already loaded
            return True
        
        plugin_path = os.path.join(self.plugins_dir, f"{plugin_name}.py")
        
        if not os.path.exists(plugin_path):
            print(f"Plugin {plugin_name} not found at {plugin_path}")
            return False
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                print(f"Failed to load plugin spec: {plugin_name}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the module has a Plugin class
            if hasattr(module, "Plugin"):
                # Create an instance of the Plugin class
                plugin_instance = module.Plugin()
                
                # Store the plugin
                self.plugins[plugin_name] = plugin_instance
                
                # Check if this is a language analyzer plugin
                if hasattr(module, "SUPPORTED_EXTENSIONS") and hasattr(module, "Analyzer"):
                    extensions = getattr(module, "SUPPORTED_EXTENSIONS", [])
                    analyzer_class = getattr(module, "Analyzer")
                    
                    # Register the analyzer for each supported extension
                    for ext in extensions:
                        self.language_analyzers[ext] = analyzer_class
                    
                    print(f"Registered language analyzer for extensions: {extensions}")
                
                return True
            else:
                # Check if this is a standalone language analyzer
                if hasattr(module, "SUPPORTED_EXTENSIONS") and hasattr(module, "Analyzer"):
                    extensions = getattr(module, "SUPPORTED_EXTENSIONS", [])
                    analyzer_class = getattr(module, "Analyzer")
                    
                    # Register the analyzer for each supported extension
                    for ext in extensions:
                        self.language_analyzers[ext] = analyzer_class
                    
                    print(f"Registered language analyzer for extensions: {extensions}")
                    return True
                else:
                    print(f"Plugin {plugin_name} does not have a Plugin class or Analyzer class")
                    return False
        except Exception as e:
            print(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """
        Load all available plugins.
        
        Returns:
            Dictionary mapping plugin names to load status
        """
        results = {}
        
        for plugin_name in self.discover_plugins():
            results[plugin_name] = self.load_plugin(plugin_name)
            
        return results
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """
        Get a loaded plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Any]:
        """
        Get all loaded plugins.
        
        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self.plugins
    
    def get_plugin_hooks(self, hook_name: str) -> List[Callable]:
        """
        Get all plugin hooks with a specific name.
        
        Args:
            hook_name: Name of the hook to find
            
        Returns:
            List of hook functions
        """
        hooks = []
        
        for plugin in self.plugins.values():
            if hasattr(plugin, hook_name) and callable(getattr(plugin, hook_name)):
                hooks.append(getattr(plugin, hook_name))
                
        return hooks
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Call a hook on all plugins that implement it.
        
        Args:
            hook_name: Name of the hook to call
            *args: Positional arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook
            
        Returns:
            List of results from each hook
        """
        results = []
        
        for hook in self.get_plugin_hooks(hook_name):
            try:
                result = hook(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error calling hook {hook_name}: {e}")
                
        return results
    
    def run_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Run hooks on all plugins that implement them.
        Alias for call_hook for backward compatibility.
        
        Args:
            hook_name: Name of the hook to call
            *args: Positional arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook
            
        Returns:
            List of results from each hook
        """
        return self.call_hook(hook_name, *args, **kwargs)
    
    def get_analyzer_for_extension(self, file_extension: str) -> Optional[Type]:
        """
        Get the appropriate analyzer class for a file extension.
        
        Args:
            file_extension: File extension (e.g., '.py', '.js')
            
        Returns:
            Analyzer class or None if not found
        """
        return self.language_analyzers.get(file_extension.lower())
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get a list of supported file extensions.
        
        Returns:
            List of supported file extensions
        """
        # Make sure plugins are loaded
        if not self.language_analyzers:
            self.load_all_plugins()
            
        # Return the keys from language_analyzers dictionary
        return list(self.language_analyzers.keys())


class PluginBase:
    """Base class for plugins to inherit from."""
    
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
        return analysis
    
    def on_suggest(self, file_path: str, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Hook called after generating suggestions.
        
        Args:
            file_path: Path to the analyzed file
            suggestions: Generated suggestions
            
        Returns:
            Modified suggestions
        """
        return suggestions
    
    def on_apply(self, file_path: str, suggestion: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook called after applying a fix.
        
        Args:
            file_path: Path to the modified file
            suggestion: Applied suggestion
            result: Result of the fix application
            
        Returns:
            Modified result
        """
        return result


class LanguageAnalyzerBase:
    """Base class for language-specific analyzers."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a file path.
        
        Args:
            file_path: Path to the file to analyze
        """
        self.file_path = file_path
        self.source_code = ""
        
    def load_file(self) -> bool:
        """
        Load the source code from the file.
        
        Returns:
            bool: True if file was loaded successfully, False otherwise
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                self.source_code = file.read()
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
    
    def extract_functions(self) -> List[Dict[str, Any]]:
        """
        Extract all functions from the code.
        
        Returns:
            List of dictionaries containing function information
        """
        raise NotImplementedError("Subclasses must implement extract_functions")
    
    def extract_classes(self) -> List[Dict[str, Any]]:
        """
        Extract all classes from the code.
        
        Returns:
            List of dictionaries containing class information
        """
        raise NotImplementedError("Subclasses must implement extract_classes")
    
    def calculate_complexity(self, code_element: Any) -> int:
        """
        Calculate cyclomatic complexity of a code element.
        
        Args:
            code_element: Code element to analyze
            
        Returns:
            Complexity score (higher means more complex)
        """
        raise NotImplementedError("Subclasses must implement calculate_complexity")
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform full analysis of the code.
        
        Returns:
            Dictionary with analysis results
        """
        if not self.source_code and not self.load_file():
            return {"error": "Failed to load file"}
        
        return {
            "file_path": self.file_path,
            "functions": self.extract_functions(),
            "classes": self.extract_classes(),
            "loc": len(self.source_code.splitlines()),
        } 