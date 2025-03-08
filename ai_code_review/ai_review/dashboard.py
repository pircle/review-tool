"""
Web dashboard for the AI Code Review Tool.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template

from .constants import LOGS_DIR
from .logger import logger
from .config_manager import config_manager

app = Flask(__name__)

def get_project_data(project_name):
    """Get all review data for a specific project."""
    # First verify this is a registered project
    project_info = config_manager.get_project(project_name)
    if not project_info:
        logger.error(f"Project {project_name} not found in projects.json")
        return None
        
    # Initialize empty data structure
    data = {
        "review_results": {
            "total_reviews": 0,
            "applied_fixes": 0,
            "pending_fixes": 0,
            "files": [],
            "applied_fixes_details": []
        },
        "ui_validation_results": {
            "validations": []
        },
        "project_info": {
            "name": project_name,
            "path": project_info.get("path", ""),
            "created_at": project_info.get("created_at"),
            "updated_at": project_info.get("updated_at")
        }
    }
    
    # Get logs directory path
    project_dir = Path(LOGS_DIR) / project_name
    if not project_dir.exists():
        logger.warning(f"Logs directory not found for project {project_name}: {project_dir}")
        return data
    
    # Read review results
    review_log = project_dir / "review_log.json"
    if review_log.exists():
        try:
            with open(review_log) as f:
                review_data = json.load(f)
                data["review_results"].update(review_data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading review log for {project_name}: {str(e)}")
    
    # Read fix results
    fix_log = project_dir / "fix_log.json"
    if fix_log.exists():
        try:
            with open(fix_log) as f:
                fix_data = json.load(f)
                data["review_results"]["applied_fixes_details"].extend(fix_data)
                data["review_results"]["applied_fixes"] = len(fix_data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading fix log for {project_name}: {str(e)}")
    
    # Read UI validation results
    ui_log = project_dir / "ui_validation_log.json"
    if ui_log.exists():
        try:
            with open(ui_log) as f:
                ui_data = json.load(f)
                data["ui_validation_results"].update(ui_data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading UI validation log for {project_name}: {str(e)}")
    
    return data

@app.route('/')
def home():
    """Render the dashboard home page."""
    return render_template('dashboard.html')

@app.route('/api/projects')
def list_projects():
    """List all registered projects with review data."""
    try:
        # Get all registered projects from config manager
        projects = []
        registered_projects = config_manager.get_projects()
        
        if not registered_projects:
            # Create projects.json if it doesn't exist
            config_manager.save_projects({})
            return jsonify([])
            
        # Convert registered_projects to a list of (name, info) tuples
        project_entries = []
        if isinstance(registered_projects, dict):
            project_entries = list(registered_projects.items())
        elif isinstance(registered_projects, list):
            project_entries = [(p.get("name", ""), p) for p in registered_projects if isinstance(p, dict)]
        else:
            logger.error(f"Unexpected projects data type: {type(registered_projects)}")
            return jsonify([])
            
        for project_name, project_info in project_entries:
            # Skip system directories and empty names
            if not project_name or project_name in ['screenshots', 'ui_reports', 'logs']:
                continue
                
            # Skip if project_info is not a dict
            if not isinstance(project_info, dict):
                logger.warning(f"Invalid project info for {project_name}: {project_info}")
                continue
                
            # Get project path and log warning if missing or invalid
            project_path = project_info.get("path", "")
            if not project_path:
                logger.warning(f"Project {project_name} has no path specified")
            elif not os.path.exists(project_path):
                logger.warning(f"Project {project_name} path does not exist: {project_path}")
                
            # Get the last review timestamp from review_log.json if it exists
            last_review = None
            review_log = Path(LOGS_DIR) / project_name / "review_log.json"
            if review_log.exists():
                try:
                    with open(review_log) as f:
                        data = json.load(f)
                        if "timestamp" in data:
                            last_review = data["timestamp"]
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error reading review log for {project_name}: {str(e)}")
            
            # Include all projects, even if path is missing or invalid
            projects.append({
                "name": project_name,
                "path": project_path,
                "last_review": last_review,
                "created_at": project_info.get("created_at"),
                "updated_at": project_info.get("updated_at")
            })
        
        return jsonify(projects)
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<project_name>')
def get_project_status(project_name):
    """Get the status and results for a specific project."""
    try:
        data = get_project_data(project_name)
        if data is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def serve_dashboard(host='localhost', port=5000, debug=False):
    """Start the dashboard server."""
    logger.info(f"Starting dashboard server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug) 