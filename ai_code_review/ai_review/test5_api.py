from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/api/test")
async def test():
    return {"message": "Test endpoint"}

@app.get("/api/projects")
async def list_projects():
    return {"projects": []}

@app.get("/api/status/{project}")
async def get_status(project: str):
    return {"status": "ok", "project": project}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5050) 