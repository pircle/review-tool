"""
Constants for the AI Code Review tool.
"""

import os
from pathlib import Path
import shutil

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Subdirectories
SCREENSHOTS_DIR = os.path.join(LOGS_DIR, "screenshots")
UI_REPORTS_DIR = os.path.join(LOGS_DIR, "ui_reports")
REPORTS_DIR = os.path.join(LOGS_DIR, "reports")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(UI_REPORTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Log file paths
CLI_LOG_PATH = os.path.join(LOGS_DIR, "cli_log.md")
VALIDATION_LOG_PATH = os.path.join(LOGS_DIR, "validation_log.md")
FIX_LOG_PATH = os.path.join(LOGS_DIR, "fix_log.json")

# Project-specific paths
def get_project_logs_dir(project_path):
    """
    Get the logs directory for a project.
    If project_path already contains a logs directory, use that.
    Otherwise, create a logs directory in the project root.
    """
    # If project_path itself is a logs directory, use its parent
    if os.path.basename(project_path) == "logs":
        project_path = os.path.dirname(project_path)
    
    # Check if project_path contains a logs directory
    logs_dir = os.path.join(project_path, "logs")
    
    # If logs_dir exists and contains another logs directory, use the outer one
    nested_logs = os.path.join(logs_dir, "logs")
    if os.path.exists(nested_logs) and os.path.isdir(nested_logs):
        # Move contents from nested logs to parent logs directory
        for item in os.listdir(nested_logs):
            src = os.path.join(nested_logs, item)
            dst = os.path.join(logs_dir, item)
            if not os.path.exists(dst):
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        # Remove the nested logs directory
        shutil.rmtree(nested_logs)
    
    # Create the logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def get_project_screenshots_dir(project_path):
    """Get the screenshots directory for a project."""
    return os.path.join(get_project_logs_dir(project_path), "screenshots")

def get_project_ui_reports_dir(project_path):
    """Get the UI reports directory for a project."""
    return os.path.join(get_project_logs_dir(project_path), "ui_reports")

def get_project_reports_dir(project_path):
    """Get the reports directory for a project."""
    return os.path.join(get_project_logs_dir(project_path), "reports") 