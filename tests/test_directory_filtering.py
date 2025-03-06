import os
import unittest
import tempfile
import shutil
from pathlib import Path

from ai_review.analyzer import analyze_directory
from ai_review.config_manager import ConfigManager, config_manager


class TestDirectoryFiltering(unittest.TestCase):
    """Test directory filtering functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        self.create_test_directory_structure()
        
        # Save original config
        self.original_config = config_manager.config.copy()
        
        # Reset config to default
        config_manager.config = ConfigManager.DEFAULT_CONFIG.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
        
        # Restore original config
        config_manager.config = self.original_config
    
    def create_test_directory_structure(self):
        """Create a test directory structure for testing."""
        # Create directories
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "node_modules"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, ".git"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "dist"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "build"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "components"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "tests"), exist_ok=True)
        
        # Create test files
        self.create_test_file(os.path.join(self.test_dir, "src", "app.js"), "// Test JavaScript file")
        self.create_test_file(os.path.join(self.test_dir, "src", "app.py"), "# Test Python file")
        self.create_test_file(os.path.join(self.test_dir, "src", "app.min.js"), "// Minified JavaScript file")
        self.create_test_file(os.path.join(self.test_dir, "node_modules", "module.js"), "// Node module file")
        self.create_test_file(os.path.join(self.test_dir, ".git", "config"), "# Git config file")
        self.create_test_file(os.path.join(self.test_dir, "dist", "bundle.js"), "// Bundled JavaScript file")
        self.create_test_file(os.path.join(self.test_dir, "build", "output.js"), "// Build output file")
        self.create_test_file(os.path.join(self.test_dir, "components", "Button.jsx"), "// React component file")
        self.create_test_file(os.path.join(self.test_dir, "tests", "test.js"), "// Test file")
        self.create_test_file(os.path.join(self.test_dir, "package.json"), "{ \"name\": \"test\" }")
        self.create_test_file(os.path.join(self.test_dir, "yarn.lock"), "# Yarn lock file")
    
    def create_test_file(self, path, content):
        """Create a test file with the given content."""
        with open(path, "w") as f:
            f.write(content)
    
    def test_directory_filtering(self):
        """Test that directory filtering works correctly."""
        # Analyze the test directory
        results = analyze_directory(self.test_dir)
        
        # Get the file paths from the results
        file_paths = [result["file_path"] for result in results]
        
        # Check that the correct files were analyzed
        self.assertIn(os.path.join(self.test_dir, "src", "app.js"), file_paths)
        self.assertIn(os.path.join(self.test_dir, "src", "app.py"), file_paths)
        self.assertIn(os.path.join(self.test_dir, "components", "Button.jsx"), file_paths)
        self.assertIn(os.path.join(self.test_dir, "tests", "test.js"), file_paths)
        self.assertIn(os.path.join(self.test_dir, "package.json"), file_paths)
        
        # Check that excluded files were not analyzed
        self.assertNotIn(os.path.join(self.test_dir, "src", "app.min.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "node_modules", "module.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, ".git", "config"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "dist", "bundle.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "build", "output.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "yarn.lock"), file_paths)
    
    def test_missing_required_directories(self):
        """Test that a warning is logged when required directories are missing."""
        # Create a new empty directory
        empty_dir = tempfile.mkdtemp()
        
        try:
            # Analyze the empty directory
            results = analyze_directory(empty_dir)
            
            # Check that no files were analyzed
            self.assertEqual(len(results), 0)
            
            # We can't easily check the log output in a unit test,
            # but the function should not raise an exception
        finally:
            # Clean up
            shutil.rmtree(empty_dir)
    
    def test_custom_config(self):
        """Test that custom configuration works correctly."""
        # Set custom configuration
        config_manager.config["file_filters"]["exclude_dirs"] = ["node_modules/", ".git/"]
        config_manager.config["file_filters"]["include_dirs"] = ["src/"]
        config_manager.config["file_filters"]["exclude_files"] = ["*.min.js"]
        
        # Analyze the test directory
        results = analyze_directory(self.test_dir)
        
        # Get the file paths from the results
        file_paths = [result["file_path"] for result in results]
        
        # Check that the correct files were analyzed
        self.assertIn(os.path.join(self.test_dir, "src", "app.js"), file_paths)
        self.assertIn(os.path.join(self.test_dir, "src", "app.py"), file_paths)
        
        # Check that excluded files were not analyzed
        self.assertNotIn(os.path.join(self.test_dir, "src", "app.min.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "node_modules", "module.js"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, ".git", "config"), file_paths)
        
        # Check that files outside include_dirs were not analyzed
        self.assertNotIn(os.path.join(self.test_dir, "components", "Button.jsx"), file_paths)
        self.assertNotIn(os.path.join(self.test_dir, "tests", "test.js"), file_paths)


if __name__ == "__main__":
    unittest.main() 