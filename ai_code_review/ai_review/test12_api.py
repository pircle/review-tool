from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/api/test")
def test():
    return {"message": "Test endpoint"}

@app.get("/api/projects")
def list_projects():
    return {"projects": []}

@app.get("/api/status/{project}")
def get_status(project: str):
    return {"status": "ok", "project": project} 