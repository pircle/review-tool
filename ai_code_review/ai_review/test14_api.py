from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/test")
def test():
    return {"message": "Test endpoint"}

@app.get("/projects")
def list_projects():
    return {"projects": []}

@app.get("/status/{project}")
def get_status(project: str):
    return {"status": "ok", "project": project}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5050, log_level="debug") 