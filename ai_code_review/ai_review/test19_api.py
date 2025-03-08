from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config_manager import ConfigManager
import logging
import os

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

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize config manager
config_manager = ConfigManager()

@app.get("/")
def root():
    """Root endpoint."""
    logger.debug("Root endpoint called")
    return {"message": "AI Code Review API"}

@app.get("/test")
def test():
    """Test endpoint."""
    logger.debug("Test endpoint called")
    return {"message": "Test endpoint"}

@app.get("/projects")
def list_projects():
    """List all registered projects."""
    logger.debug("Projects endpoint called")
    try:
        projects = config_manager.get_projects()
        logger.debug(f"Found {len(projects)} projects")
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{project}")
def get_status(project: str):
    """Get status of a specific project."""
    logger.debug(f"Status endpoint called for project: {project}")
    try:
        project_data = config_manager.get_project(project)
        if not project_data:
            logger.warning(f"Project not found: {project}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.debug(f"Found project data: {project_data}")
        return project_data
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting project status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=5050, log_level="debug") 