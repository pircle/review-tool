from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
    return {"message": "Test endpoint"}

@api_router.get("/projects")
async def list_projects():
    return {"projects": []}

@api_router.get("/status/{project}")
async def get_status(project: str):
    return {"status": "ok", "project": project}

# Include API router
app.include_router(api_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Hello World"}

def start_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=5050, log_level="debug")
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    start_server() 