from fastapi import FastAPI, APIRouter

app = FastAPI()
api_router = APIRouter(prefix="/api")

@api_router.get("/test")
async def test():
    return {"message": "Test endpoint"}

@api_router.get("/projects")
async def list_projects():
    return {"projects": []}

app.include_router(api_router) 