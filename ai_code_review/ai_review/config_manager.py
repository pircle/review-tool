import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration settings for the AI Code Review tool.
    Handles loading from config files and providing default values.
    Supports project-specific configurations.
    """
    
    DEFAULT_CONFIG = {
        "openai_api_key": "",
        "model": "gpt-4o",
        "complexity_threshold": 5,
        "log_level": "INFO",
        "file_filters": {
            "exclude_dirs": [
                "node_modules/",
                ".git/",
                "__pycache__/",
                "venv/",
                "env/",
                ".venv/",
                "dist/",
                "build/",
                ".next/",
                "out/",
                "coverage/",
                "logs/"
            ],
            "include_dirs": [
                "src/",
                "app/",
                "backend/",
                "frontend/",
                "lib/",
                "utils/",
                "components/",
                "services/",
                "api/",
                "tests/",
                "pages/",
                "server/",
                "config/"
            ],
            "exclude_files": [
                "*.min.js",
                "*.bundle.js",
                "*.map",
                "*.lock",
                "package-lock.json",
                "yarn.lock",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.so",
                "*.dll",
                "*.exe"
            ]
        }
    }
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_dir = os.path.expanduser("~/.ai-code-review")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.local_config_file = "config.json"
        self.projects_file = os.path.join(self.config_dir, "projects.json")
        self.current_project = None
        self.project_config_file = None
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize projects list
        self.projects = self._load_projects()
        
        # Load global configuration
        self._load_config()
    
    def _load_projects(self):
        """Load the list of projects."""
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading projects file: {str(e)}")
        
        # Return empty projects list if file doesn't exist or there's an error
        return {"projects": []}
    
    def _save_projects(self):
        """Save the list of projects."""
        try:
            with open(self.projects_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
                logger.debug(f"Saved projects list to {self.projects_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving projects file: {str(e)}")
            return False
    
    def get_projects(self):
        """Get the list of projects."""
        return self.projects.get("projects", [])
    
    def add_project(self, project_name, project_path):
        """Add a new project to the list."""
        projects = self.get_projects()
        
        # Check if project already exists
        for project in projects:
            if project["name"] == project_name:
                logger.warning(f"Project '{project_name}' already exists")
                return False
        
        # Add new project
        projects.append({
            "name": project_name,
            "path": project_path
        })
        
        self.projects["projects"] = projects
        return self._save_projects()
    
    def get_project(self, project_name):
        """Get a project by name."""
        for project in self.get_projects():
            if project["name"] == project_name:
                return project
        return None
    
    def set_current_project(self, project_name):
        """Set the current project."""
        project = self.get_project(project_name)
        if not project:
            logger.error(f"Project '{project_name}' not found")
            return False
        
        self.current_project = project
        self.project_config_file = os.path.join(project["path"], "config.json")
        
        # Load project-specific configuration
        self._load_project_config()
        return True
    
    def _load_project_config(self):
        """Load project-specific configuration."""
        if not self.current_project:
            logger.warning("No current project set")
            return
        
        # Reset to default configuration
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load global configuration
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    global_config = json.load(f)
                    self._merge_config(global_config)
                    logger.debug(f"Loaded global configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading global config file: {str(e)}")
        
        # Load project-specific configuration
        if os.path.exists(self.project_config_file):
            try:
                with open(self.project_config_file, 'r') as f:
                    project_config = json.load(f)
                    self._merge_config(project_config)
                    logger.debug(f"Loaded project configuration from {self.project_config_file}")
            except Exception as e:
                logger.error(f"Error loading project config file: {str(e)}")
    
    def _load_config(self):
        """Load configuration from global and local config files."""
        # Load global config if it exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    global_config = json.load(f)
                    self._merge_config(global_config)
                    logger.debug(f"Loaded global configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading global config file: {str(e)}")
        
        # Load local config if it exists (overrides global)
        if os.path.exists(self.local_config_file):
            try:
                with open(self.local_config_file, 'r') as f:
                    local_config = json.load(f)
                    self._merge_config(local_config)
                    logger.debug(f"Loaded local configuration from {self.local_config_file}")
            except Exception as e:
                logger.error(f"Error loading local config file: {str(e)}")
    
    def _merge_config(self, new_config):
        """Merge new configuration with existing configuration."""
        for key, value in new_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                # If both are dictionaries, merge them
                self.config[key].update(value)
            else:
                # Otherwise, replace the value
                self.config[key] = value
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value
    
    def save(self):
        """Save the configuration to the global config file."""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.debug(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}")
            return False
    
    def save_local(self):
        """Save the configuration to a local config file."""
        try:
            with open(self.local_config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.debug(f"Saved local configuration to {self.local_config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving local config file: {str(e)}")
            return False
    
    def save_project_config(self):
        """Save the configuration to the project config file."""
        if not self.current_project:
            logger.warning("No current project set")
            return False
        
        try:
            # Create project directory if it doesn't exist
            project_dir = self.current_project["path"]
            os.makedirs(project_dir, exist_ok=True)
            
            with open(self.project_config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.debug(f"Saved project configuration to {self.project_config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving project config file: {str(e)}")
            return False
    
    def get_project_logs_dir(self):
        """Get the logs directory for the current project."""
        if not self.current_project:
            logger.warning("No current project set")
            return None
        
        logs_dir = os.path.join(self.current_project["path"], "logs")
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir
    
    def get_project_reports_dir(self):
        """Get the reports directory for the current project."""
        if not self.current_project:
            logger.warning("No current project set")
            return None
        
        logs_dir = self.get_project_logs_dir()
        if not logs_dir:
            return None
        
        reports_dir = os.path.join(logs_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        return reports_dir
    
    def should_exclude_path(self, path):
        """
        Check if a path should be excluded based on configuration.
        
        Args:
            path (str): The path to check
            
        Returns:
            bool: True if the path should be excluded, False otherwise
        """
        path = Path(path)
        
        # Check if path is in excluded directories
        for exclude_dir in self.config["file_filters"]["exclude_dirs"]:
            exclude_path = Path(exclude_dir.rstrip('/'))
            if exclude_path.parts and any(part == exclude_path.parts[0] for part in path.parts):
                logger.debug(f"Excluding path (excluded dir): {path}")
                return True
        
        # Check if path matches excluded file patterns
        for exclude_pattern in self.config["file_filters"]["exclude_files"]:
            if path.match(exclude_pattern):
                logger.debug(f"Excluding path (excluded file pattern): {path}")
                return True
        
        # If include_dirs is specified and not empty, check if path is in included directories
        include_dirs = self.config["file_filters"]["include_dirs"]
        if include_dirs:
            # If path doesn't start with any of the include_dirs, exclude it
            if not any(str(path).startswith(include_dir.rstrip('/')) for include_dir in include_dirs):
                # Special case: if path is a direct file in the root, include it
                if len(path.parts) == 1:
                    return False
                logger.debug(f"Excluding path (not in included dirs): {path}")
                return True
        
        return False

# Create a singleton instance
config_manager = ConfigManager() 