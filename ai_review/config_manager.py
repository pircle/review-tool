"""Configuration management for the AI Code Review tool."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import datetime

# Configure logging
LOG_DIR = os.path.expanduser("~/.ai-code-review/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "system.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the AI Code Review tool."""
    
    # Default configuration settings
    DEFAULT_CONFIG = {
        "log_level": "INFO",
        "complexity_threshold": 5,
        "monitored_extensions": [".py", ".json", ".md", ".yml", ".yaml"],
        "file_filters": {
            "exclude_dirs": [
                ".git",
                "__pycache__",
                "node_modules",
                "venv",
                ".env"
            ],
            "exclude_files": [
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.so",
                "*.dll",
                "*.dylib"
            ],
            "include_dirs": []
        },
        "validation": {
            "max_line_length": 100,
            "max_function_length": 50,
            "require_docstrings": True,
            "indent_size": 4,
            "indent_style": "spaces"
        },
        "review": {
            "auto_fix": True,
            "max_fix_attempts": 3,
            "review_batch_size": 10,
            "review_interval": 300
        }
    }
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._config_dir = None
        self._config_file = None
        self._projects_file = None
        self.config = None
        self.local_config_file = "config.json"
        self.current_project = None
        self.project_config_file = None
        self.projects = None
        
        # Initialize configuration
        self.config_dir = self._get_config_dir()
        
    @property
    def config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir
    
    @config_dir.setter
    def config_dir(self, value: Path):
        """Set the configuration directory path."""
        self._config_dir = Path(value)
        self._config_file = self._config_dir / "config.json"
        self._projects_file = self._config_dir / "projects.json"
        
        # Create config directory if it doesn't exist
        os.makedirs(self._config_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize projects list
        self.projects = self._load_projects()
        
        # Validate configuration
        self._validate_config()
    
    @property
    def config_file(self) -> Path:
        """Get the configuration file path."""
        return self._config_file
    
    @property
    def projects_file(self) -> Path:
        """Get the projects file path."""
        return self._projects_file
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory path.
        
        Returns:
            Path to the configuration directory
        """
        config_dir = os.getenv("AI_CODE_REVIEW_CONFIG_DIR")
        if config_dir:
            return Path(config_dir)
        return Path.home() / ".ai-code-review"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
        
        if not self.config_file.exists():
            with open(self.config_file, "w") as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)
            return self.DEFAULT_CONFIG
        
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                # Update with any missing default values
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return self.DEFAULT_CONFIG
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
        self._save_config()
    
    def _save_config(self) -> bool:
        """Save global configuration to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Save configuration
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            
            logger.debug(f"Saved global configuration to {self.config_file}")
            return True
            
        except OSError as e:
            logger.error(f"Error saving global configuration: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving global configuration: {str(e)}")
            return False
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values.
        
        Args:
            updates: Dictionary of updates to apply
        """
        self.config.update(updates)
        self._save_config()
    
    def _validate_config(self):
        """Validate the configuration and ensure all required fields are present."""
        missing_fields = []
        for field in ["complexity_threshold", "log_level"]:
            if not self.config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Missing required configuration fields: {', '.join(missing_fields)}")
            logger.error(f"Please update your configuration file at {self.config_file}")
            self._create_example_config()
            
            # Don't raise error if only complexity_threshold is missing during initialization
            if len(missing_fields) == 1 and missing_fields[0] == "complexity_threshold":
                logger.warning("Complexity threshold is missing but will be required for AI features")
                return
            
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
    
    def _create_example_config(self):
        """Create an example configuration file if it doesn't exist."""
        example_file = self.config_dir / "config.json.example"
        if not example_file.exists():
            try:
                with open(example_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
                logger.info(f"Created example configuration file at {example_file}")
            except Exception as e:
                logger.error(f"Error creating example config file: {str(e)}")
    
    def _load_projects(self):
        """Load the list of projects."""
        # Remember current project
        current_project = self.current_project
        current_project_config_file = self.project_config_file
        
        if self.projects_file.exists():
            try:
                with open(self.projects_file, 'r') as f:
                    projects_data = json.load(f)
                    
                    # Ensure all projects have timestamps
                    if "projects" in projects_data:
                        current_time = datetime.datetime.now().isoformat()
                        for project in projects_data["projects"]:
                            if not project.get("created_at"):
                                project["created_at"] = current_time
                            if not project.get("updated_at"):
                                project["updated_at"] = current_time
                            if not project.get("last_review"):
                                project["last_review"] = current_time
                                logger.warning(f"Missing last_review for project {project.get('name')}, adding default")
                        
                        # Save any added timestamps
                        with open(self.projects_file, 'w') as f:
                            json.dump(projects_data, f, indent=2)
                        
                    # Restore current project
                    self.current_project = current_project
                    self.project_config_file = current_project_config_file
                    
                    return projects_data
            except Exception as e:
                logger.error(f"Error loading projects file: {str(e)}")
        
        # Create default projects file if it doesn't exist
        default_projects = {"projects": []}
        try:
            with open(self.projects_file, 'w') as f:
                json.dump(default_projects, f, indent=2)
            logger.info(f"Created default projects file at {self.projects_file}")
        except Exception as e:
            logger.error(f"Error creating default projects file: {str(e)}")
        
        # Restore current project
        self.current_project = current_project
        self.project_config_file = current_project_config_file
        
        return default_projects
    
    def _save_projects(self) -> bool:
        """Save the list of projects.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)
            
            # Save projects list
            with open(self.projects_file, 'w') as f:
                json.dump(self.projects, f, indent=2)
            
            logger.debug(f"Saved projects list to {self.projects_file}")
            
            # Reload projects list
            self.projects = self._load_projects()
            
            return True
            
        except OSError as e:
            logger.error(f"Error saving projects list: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving projects list: {str(e)}")
            return False
    
    def get_projects(self):
        """Get the list of projects."""
        return self.projects.get("projects", [])
    
    def add_project(self, name: str, path: str) -> bool:
        """Add a new project."""
        try:
            # Normalize path
            path = os.path.abspath(path)
            
            # Check if project already exists
            if self.get_project(name):
                logger.warning(f"Project '{name}' already exists")
                return False
            
            # Check if path is already registered
            for project in self.get_projects():
                if os.path.abspath(project["path"]) == path:
                    logger.warning(f"Path '{path}' is already registered to project '{project['name']}'")
                    return False
            
            # Create project entry with timestamps
            current_time = datetime.datetime.now().isoformat()
            project = {
                "name": name,
                "path": path,
                "created_at": current_time,
                "updated_at": current_time,
                "last_review": current_time
            }
            
            # Add to projects list
            if "projects" not in self.projects:
                self.projects["projects"] = []
            self.projects["projects"].append(project)
            
            # Save changes
            if self._save_projects():
                logger.info(f"Added project '{name}' at path '{path}'")
                # Set as current project
                self.current_project = name
                self.project_config_file = os.path.join(path, "config.json")
                return True
            
            logger.error(f"Failed to save project '{name}'")
            return False
        except Exception as e:
            logger.error(f"Error adding project: {str(e)}")
            return False
    
    def get_project(self, project_name):
        """Get a project by name."""
        logger.debug(f"Looking for project: {project_name}")
        logger.debug(f"All projects: {self.get_projects()}")
        for project in self.get_projects():
            if project["name"] == project_name:
                logger.debug(f"Found project: {project}")
                return project
        logger.warning(f"Project not found: {project_name}")
        return None
    
    def set_current_project(self, project_name):
        """Set the current project."""
        project = self.get_project(project_name)
        if not project:
            logger.error(f"Project '{project_name}' not found")
            return False
        
        self.current_project = project_name
        self.project_config_file = os.path.join(project["path"], "config.json")
        
        # Load project-specific configuration
        self._load_project_config()
        logger.info(f"Current project set to '{project_name}'")
        return True
    
    def _load_project_config(self):
        """Load project-specific configuration."""
        if not self.current_project:
            logger.warning("No current project set")
            return
        
        # Get the project by name
        project = self.get_project(self.current_project)
        if not project:
            logger.warning(f"Project '{self.current_project}' not found")
            return
        
        # Reset to default configuration
        self.config = self._load_config()
        
        # Load project-specific configuration
        if os.path.exists(self.project_config_file):
            try:
                with open(self.project_config_file, 'r') as f:
                    project_config = json.load(f)
                    self.config.update(project_config)
                    logger.debug(f"Loaded project configuration from {self.project_config_file}")
            except Exception as e:
                logger.error(f"Error loading project config file: {str(e)}")
    
    def get_project_logs_dir(self):
        """Get the logs directory for the current project."""
        if self.current_project:
            project = self.get_project(self.current_project)
            if project:
                logs_dir = os.path.join(project["path"], "logs")
                os.makedirs(logs_dir, exist_ok=True)
                logger.debug(f"Using project logs directory: {logs_dir}")
                return logs_dir
        
        # Fallback to default logs directory
        logs_dir = os.path.join(os.path.dirname(self.config_file), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        logger.debug(f"Using default logs directory: {logs_dir}")
        return logs_dir
    
    def get_project_reports_dir(self):
        """Get the reports directory for the current project."""
        if self.current_project:
            project = self.get_project(self.current_project)
            if project:
                reports_dir = os.path.join(project["path"], "reports")
                os.makedirs(reports_dir, exist_ok=True)
                logger.debug(f"Using project reports directory: {reports_dir}")
                return reports_dir
        
        # Fallback to default reports directory
        reports_dir = os.path.join(os.path.dirname(self.config_file), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        logger.debug(f"Using default reports directory: {reports_dir}")
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

    def update_project(self, project_name, **kwargs):
        """Update a project's information."""
        projects = self.get_projects()
        
        for project in projects:
            if project["name"] == project_name:
                # Update provided fields
                for key, value in kwargs.items():
                    project[key] = value
                
                # Always update the updated_at timestamp
                current_time = datetime.datetime.now().isoformat()
                project["updated_at"] = current_time
                
                # Ensure last_review exists
                if "last_review" not in project:
                    project["last_review"] = current_time
                    logger.warning(f"Added missing last_review for project {project_name}")
                
                # Save changes
                self.projects["projects"] = projects
                if self._save_projects():
                    logger.info(f"Project '{project_name}' updated successfully")
                    return True
                
                logger.error(f"Failed to save project updates for '{project_name}'")
                return False
        
        logger.warning(f"Project '{project_name}' not found")
        return False

    def update_project_review(self, project_name: str) -> bool:
        """Update a project's last review timestamp."""
        try:
            projects = self.get_projects()
            for project in projects:
                if project["name"] == project_name:
                    # Update timestamps
                    current_time = datetime.now().isoformat()
                    project["last_review"] = current_time
                    project["updated_at"] = current_time
                    
                    # Save changes
                    self.projects["projects"] = projects
                    if self._save_projects():
                        logger.info(f"Updated last review timestamp for project '{project_name}'")
                        return True
                    
                    logger.error(f"Failed to save review timestamp for '{project_name}'")
                    return False
            
            logger.warning(f"Project '{project_name}' not found")
            return False
        except Exception as e:
            logger.error(f"Error updating project review timestamp: {str(e)}")
            return False

    def get_file_filters(self):
        """Get file filters from configuration."""
        return self.config.get("file_filters", self._load_config()["file_filters"])

    def save_project_config(self) -> bool:
        """Save project-specific configuration.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.current_project:
            logger.warning("No current project set")
            return False
        
        project = self.get_project(self.current_project)
        if not project:
            logger.warning(f"Project '{self.current_project}' not found")
            return False
        
        try:
            # Create project directory if it doesn't exist
            project_dir = project["path"]
            os.makedirs(project_dir, exist_ok=True)
            
            # Save configuration
            with open(self.project_config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            # Update project timestamps
            current_time = datetime.datetime.now().isoformat()
            self.update_project(self.current_project, updated_at=current_time)
            
            logger.info(f"Saved project configuration to {self.project_config_file}")
            return True
            
        except OSError as e:
            logger.error(f"Error saving project configuration: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving project configuration: {str(e)}")
            return False

# Create a singleton instance
config_manager = ConfigManager() 