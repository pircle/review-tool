from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"projects": []}

@app.get("/status/{project}")
def get_status(project: str):
    logger.debug(f"Status endpoint called for project: {project}")
    return {"status": "ok", "project": project}

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=5050, log_level="debug") 