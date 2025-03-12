from fastapi import FastAPI, HTTPException
from .config_manager import ConfigManager

app = FastAPI()
config_manager = ConfigManager()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint"}

@app.get("/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods)
        })
    return routes

@app.get("/api/projects")
async def list_projects():
    try:
        projects = config_manager.get_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{project}")
async def get_status(project: str):
    try:
        project_data = config_manager.get_project(project)
        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 