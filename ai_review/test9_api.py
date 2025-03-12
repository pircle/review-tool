from fastapi import FastAPI, APIRouter
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

# Create API router
api_router = APIRouter(prefix="/api")

@api_router.get("/test")
async def test():
    logger.debug("Test endpoint called")
    return {"message": "Test endpoint"}

@api_router.get("/projects")
async def list_projects():
    logger.debug("Projects endpoint called")
    return {"projects": []}

@api_router.get("/status/{project}")
async def get_status(project: str):
    logger.debug(f"Status endpoint called for project: {project}")
    return {"status": "ok", "project": project}

# Include API router
app.include_router(api_router)

# Root endpoint
@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"message": "Hello World"}

def start_server():
    logger.info("Starting server...")
    config = uvicorn.Config(app, host="127.0.0.1", port=5050, log_level="debug")
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    start_server() 