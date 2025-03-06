import os
import unittest
import tempfile
import shutil
from pathlib import Path

from ai_review.config_manager import ConfigManager, config_manager


class TestMultiProjectSupport(unittest.TestCase):
    """Test multi-project support functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp()
        self.project_a_dir = os.path.join(self.test_dir, "ProjectA")
        self.project_b_dir = os.path.join(self.test_dir, "ProjectB")
        
        # Create project directories
        os.makedirs(self.project_a_dir, exist_ok=True)
        os.makedirs(self.project_b_dir, exist_ok=True)
        
        # Save original config
        self.original_config = config_manager.config.copy()
        self.original_projects = config_manager.projects.copy()
        
        # Reset config to default
        config_manager.config = ConfigManager.DEFAULT_CONFIG.copy()
        config_manager.projects = {"projects": []}
        
        # Add test projects
        config_manager.add_project("ProjectA", self.project_a_dir)
        config_manager.add_project("ProjectB", self.project_b_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
        
        # Restore original config and projects
        config_manager.config = self.original_config
        config_manager.projects = self.original_projects
        config_manager.current_project = None
        config_manager.project_config_file = None
    
    def test_project_creation(self):
        """Test that projects can be created."""
        # Check that projects were added
        projects = config_manager.get_projects()
        self.assertEqual(len(projects), 2)
        
        # Check project names
        project_names = [p["name"] for p in projects]
        self.assertIn("ProjectA", project_names)
        self.assertIn("ProjectB", project_names)
        
        # Check project paths
        project_paths = [p["path"] for p in projects]
        self.assertIn(self.project_a_dir, project_paths)
        self.assertIn(self.project_b_dir, project_paths)
    
    def test_project_selection(self):
        """Test that projects can be selected."""
        # Select ProjectA
        result = config_manager.set_current_project("ProjectA")
        self.assertTrue(result)
        self.assertEqual(config_manager.current_project["name"], "ProjectA")
        self.assertEqual(config_manager.current_project["path"], self.project_a_dir)
        
        # Select ProjectB
        result = config_manager.set_current_project("ProjectB")
        self.assertTrue(result)
        self.assertEqual(config_manager.current_project["name"], "ProjectB")
        self.assertEqual(config_manager.current_project["path"], self.project_b_dir)
        
        # Try to select non-existent project
        result = config_manager.set_current_project("ProjectC")
        self.assertFalse(result)
    
    def test_project_config(self):
        """Test that project-specific configurations work."""
        # Select ProjectA
        config_manager.set_current_project("ProjectA")
        
        # Set a configuration value
        config_manager.set("complexity_threshold", 10)
        
        # Save the configuration
        result = config_manager.save_project_config()
        self.assertTrue(result)
        
        # Check that the configuration file was created
        config_file = os.path.join(self.project_a_dir, "config.json")
        self.assertTrue(os.path.exists(config_file))
        
        # Select ProjectB
        config_manager.set_current_project("ProjectB")
        
        # Set a different configuration value
        config_manager.set("complexity_threshold", 5)
        
        # Save the configuration
        result = config_manager.save_project_config()
        self.assertTrue(result)
        
        # Check that the configuration file was created
        config_file = os.path.join(self.project_b_dir, "config.json")
        self.assertTrue(os.path.exists(config_file))
        
        # Select ProjectA again
        config_manager.set_current_project("ProjectA")
        
        # Check that the configuration value is correct
        self.assertEqual(config_manager.get("complexity_threshold"), 10)
        
        # Select ProjectB again
        config_manager.set_current_project("ProjectB")
        
        # Check that the configuration value is correct
        self.assertEqual(config_manager.get("complexity_threshold"), 5)
    
    def test_project_logs_dir(self):
        """Test that project-specific logs directories work."""
        # Select ProjectA
        config_manager.set_current_project("ProjectA")
        
        # Get logs directory
        logs_dir = config_manager.get_project_logs_dir()
        self.assertEqual(logs_dir, os.path.join(self.project_a_dir, "logs"))
        
        # Check that the logs directory was created
        self.assertTrue(os.path.exists(logs_dir))
        
        # Select ProjectB
        config_manager.set_current_project("ProjectB")
        
        # Get logs directory
        logs_dir = config_manager.get_project_logs_dir()
        self.assertEqual(logs_dir, os.path.join(self.project_b_dir, "logs"))
        
        # Check that the logs directory was created
        self.assertTrue(os.path.exists(logs_dir))
    
    def test_project_reports_dir(self):
        """Test that project-specific reports directories work."""
        # Select ProjectA
        config_manager.set_current_project("ProjectA")
        
        # Get reports directory
        reports_dir = config_manager.get_project_reports_dir()
        self.assertEqual(reports_dir, os.path.join(self.project_a_dir, "logs", "reports"))
        
        # Check that the reports directory was created
        self.assertTrue(os.path.exists(reports_dir))
        
        # Select ProjectB
        config_manager.set_current_project("ProjectB")
        
        # Get reports directory
        reports_dir = config_manager.get_project_reports_dir()
        self.assertEqual(reports_dir, os.path.join(self.project_b_dir, "logs", "reports"))
        
        # Check that the reports directory was created
        self.assertTrue(os.path.exists(reports_dir))


if __name__ == "__main__":
    unittest.main()
