from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
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

def start_server():
    logger.info("Starting server...")
    try:
        config = uvicorn.Config(app, host="127.0.0.1", port=5050, log_level="debug")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise

if __name__ == "__main__":
    start_server() 