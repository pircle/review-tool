import os
import json
import logging
from pathlib import Path
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
    """
    Manages configuration settings for the AI Code Review tool.
    Handles loading from config files and providing default values.
    Supports project-specific configurations.
    """
    
    DEFAULT_CONFIG = {
        "openai_api_key": "",
        "model": "gpt-4",
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
    
    REQUIRED_FIELDS = ["openai_api_key", "model", "complexity_threshold", "log_level"]
    
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
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the configuration and ensure all required fields are present."""
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if not self.config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Missing required configuration fields: {', '.join(missing_fields)}")
            logger.error(f"Please update your configuration file at {self.config_file}")
            self._create_example_config()
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
    
    def _create_example_config(self):
        """Create an example configuration file if it doesn't exist."""
        example_file = os.path.join(os.path.dirname(self.config_file), "config.json.example")
        if not os.path.exists(example_file):
            try:
                with open(example_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=2)
                logger.info(f"Created example configuration file at {example_file}")
            except Exception as e:
                logger.error(f"Error creating example config file: {str(e)}")
    
    def _load_projects(self):
        """Load the list of projects."""
        if os.path.exists(self.projects_file):
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
        
        return default_projects
    
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
        
        # Set project config file path
        self.project_config_file = os.path.join(project["path"], "config.json")
        
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
        # Create default config if it doesn't exist
        if not os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.DEFAULT_CONFIG, f, indent=2)
                logger.info(f"Created default configuration file at {self.config_file}")
                self._create_example_config()
            except Exception as e:
                logger.error(f"Error creating default config file: {str(e)}")
        
        # Load global config if it exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    global_config = json.load(f)
                    self._merge_config(global_config)
                    logger.debug(f"Loaded global configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading global config file: {str(e)}")
    
    def _merge_config(self, new_config):
        """Merge new configuration with existing configuration."""
        try:
            for key, value in new_config.items():
                if isinstance(value, dict) and key in self.config and isinstance(self.config[key], dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
        except Exception as e:
            logger.error(f"Error merging configurations: {str(e)}")
    
    def get_config(self):
        """Get the current configuration."""
        return self.config
    
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
        
        # Get the project by name
        project = self.get_project(self.current_project)
        if not project:
            logger.warning(f"Project '{self.current_project}' not found")
            return False
        
        try:
            # Create project directory if it doesn't exist
            project_dir = project["path"]
            os.makedirs(project_dir, exist_ok=True)
            
            # Ensure project_config_file is set correctly
            self.project_config_file = os.path.join(project_dir, "config.json")
            
            with open(self.project_config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.debug(f"Saved project configuration to {self.project_config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving project config file: {str(e)}")
            return False
    
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

# Create a singleton instance
config_manager = ConfigManager() 