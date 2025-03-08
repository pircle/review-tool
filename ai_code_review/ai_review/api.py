"""
API server for the AI Code Review Tool.
Provides endpoints to trigger AI reviews and UI validations programmatically.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from pathlib import Path

from .ui_validator import validate_ui
from .logger import logger
from .config_manager import config_manager
from .constants import LOGS_DIR, get_project_logs_dir

app = FastAPI(
    title="AI Code Review API",
    description="API for automated code review and UI validation",
    version="1.0.0"
)

# Models for request validation
class ProjectInfo(BaseModel):
    """Model for project information."""
    name: str
    path: str
    last_review: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ReviewRequest(BaseModel):
    path: str
    project: Optional[str] = None
    complexity_threshold: int = 5
    ai: bool = True
    model: str = "gpt-4o"
    apply_fixes: bool = False
    security_scan: bool = False
    dependency_scan: bool = False
    generate_report: bool = True
    report_format: str = "json"
    auto_fix: bool = False
    api_key: Optional[str] = None

class UIValidationRequest(BaseModel):
    url: str
    project: Optional[str] = None
    report_format: str = "markdown"
    api_key: Optional[str] = None

class AutoFixRequest(BaseModel):
    path: str
    project: Optional[str] = None
    fixes: List[Dict[str, Any]]
    api_key: Optional[str] = None

@app.get("/api/projects", response_model=List[ProjectInfo])
async def list_projects():
    """List all registered projects with review data."""
    try:
        # Get all registered projects from config manager
        projects = []
        registered_projects = config_manager.get_projects()
        
        if not registered_projects:
            # Create projects.json if it doesn't exist
            config_manager.save_projects({})
            return []
            
        # Convert registered_projects to a list of (name, info) tuples
        project_entries = []
        if isinstance(registered_projects, dict):
            project_entries = list(registered_projects.items())
        elif isinstance(registered_projects, list):
            project_entries = [(p.get("name", ""), p) for p in registered_projects if isinstance(p, dict)]
        else:
            logger.error(f"Unexpected projects data type: {type(registered_projects)}")
            return []
            
        # Get current time for default timestamps
        current_time = datetime.now().isoformat()
            
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
                
            # Get timestamps with defaults
            created_at = project_info.get("created_at")
            updated_at = project_info.get("updated_at")
            last_review = project_info.get("last_review")
            
            # If timestamps are missing, add them and update the project
            needs_update = False
            if not created_at:
                created_at = current_time
                needs_update = True
            if not updated_at:
                updated_at = current_time
                needs_update = True
            if not last_review:
                last_review = current_time
                needs_update = True
                logger.warning(f"Missing last_review for project {project_name}, adding default")
            
            if needs_update:
                config_manager.update_project(
                    project_name,
                    created_at=created_at,
                    updated_at=updated_at,
                    last_review=last_review
                )
            
            # Include all projects, even if path is missing or invalid
            projects.append(ProjectInfo(
                name=project_name,
                path=project_path,
                last_review=last_review,
                created_at=created_at,
                updated_at=updated_at
            ))
        
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task to run code review
async def run_code_review(request: ReviewRequest) -> Dict[str, Any]:
    """Run code review in the background."""
    try:
        # Verify project exists if provided
        if request.project and not config_manager.get_project(request.project):
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project}")
        
        # Set up project context if provided
        if request.project:
            config_manager.set_current_project(request.project)
        
        # Import review_code here to avoid circular import
        from .cli import review_code
        
        # Run the review
        result = review_code(
            path=request.path,
            complexity_threshold=request.complexity_threshold,
            ai=request.ai,
            api_key=request.api_key,
            model=request.model,
            apply_fixes=request.apply_fixes,
            security_scan=request.security_scan,
            dependency_scan=request.dependency_scan,
            generate_report=request.generate_report,
            report_format=request.report_format,
            project=request.project
        )
        
        # Update last_review timestamp if project is provided
        if request.project:
            config_manager.update_project_review(request.project)
        
        # Store results in project logs
        if request.project:
            project = config_manager.get_project(request.project)
            if project:
                logs_dir = get_project_logs_dir(project["path"])
                results_file = os.path.join(logs_dir, "review_results.json")
                with open(results_file, "w") as f:
                    json.dump(result, f, indent=2)
        
        return result
    except Exception as e:
        logger.error(f"Error in code review: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task to run UI validation
async def run_ui_validation(request: UIValidationRequest) -> Dict[str, Any]:
    """Run UI validation in the background."""
    try:
        # Set up project context if provided
        if request.project:
            config_manager.set_current_project(request.project)
        
        # Run the validation
        result = validate_ui(
            url=request.url,
            api_key=request.api_key,
            report_format=request.report_format
        )
        
        # Store results in project logs
        if request.project:
            project = config_manager.get_project(request.project)
            if project:
                logs_dir = get_project_logs_dir(project["path"])
                results_file = os.path.join(logs_dir, "ui_validation_results.json")
                with open(results_file, "w") as f:
                    json.dump(result, f, indent=2)
        
        return result
    except Exception as e:
        logger.error(f"Error in UI validation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review")
async def trigger_review(request: ReviewRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger an AI code review.
    
    Args:
        request: Review request parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        Dictionary containing review status and task ID
    """
    try:
        # Validate path
        if not os.path.exists(request.path):
            raise HTTPException(status_code=400, detail=f"Path does not exist: {request.path}")
        
        # Start review in background
        background_tasks.add_task(run_code_review, request)
        
        return {
            "status": "success",
            "message": "Code review started",
            "path": request.path,
            "project": request.project
        }
    except Exception as e:
        logger.error(f"Error triggering review: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate-ui")
async def trigger_ui_validation(request: UIValidationRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger UI validation.
    
    Args:
        request: UI validation request parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        Dictionary containing validation status and task ID
    """
    try:
        # Start validation in background
        background_tasks.add_task(run_ui_validation, request)
        
        return {
            "status": "success",
            "message": "UI validation started",
            "url": request.url,
            "project": request.project
        }
    except Exception as e:
        logger.error(f"Error triggering UI validation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_project_data(project_name):
    """Get all review data for a specific project."""
    # First verify this is a registered project
    project_info = config_manager.get_project(project_name)
    if not project_info:
        logger.error(f"Project {project_name} not found in projects.json")
        return None
        
    # Get last_review with default value
    last_review = project_info.get("last_review", "No reviews yet")
        
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
            "updated_at": project_info.get("updated_at"),
            "last_review": last_review
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
                
                # Update last_review if timestamp exists in review_log
                if "timestamp" in review_data:
                    data["project_info"]["last_review"] = review_data["timestamp"]
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

@app.get("/status/{project}")
async def get_status(project: str) -> Dict[str, Any]:
    """
    Get the status of reviews and validations for a project.
    
    Args:
        project: Project name
        
    Returns:
        Dictionary containing project status
    """
    try:
        # Get project data
        data = get_project_data(project)
        if data is None:
            raise HTTPException(status_code=404, detail=f"Project not found: {project}")
        
        return data
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server."""
    uvicorn.run(app, host=host, port=port)

def serve_dashboard(host='localhost', port=5000, debug=False):
    """Start the dashboard server."""
    app.run(host=host, port=port, debug=debug) 