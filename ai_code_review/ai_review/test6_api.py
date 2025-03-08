from fastapi import FastAPI, APIRouter

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

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

app.include_router(api_router)

def run_server():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5050)

if __name__ == "__main__":
    run_server() 