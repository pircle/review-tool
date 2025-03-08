from fastapi import FastAPI, HTTPException
from .config_manager import ConfigManager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize config manager
config_manager = ConfigManager()

@app.get("/")
def root():
    logger.debug("Root endpoint called")
    return {"message": "Hello World"}

@app.get("/test")
def test():
    logger.debug("Test endpoint called")
    return {"message": "Test endpoint"}

@app.get("/projects")
def list_projects():
    logger.debug("Projects endpoint called")
    try:
        projects = config_manager.get_projects()
        logger.debug(f"Found projects: {projects}")
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{project}")
def get_status(project: str):
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