from fastapi import FastAPI
from backend.api import invocations
from backend.database import db
from backend.containers.docker_manager import docker_manager

# Initialize Database on startup
db.init_db()

app = FastAPI(title="LambdaX API (Phase 2)")

# Include invocation routes
app.include_router(invocations.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/containers")
def list_containers():
    containers = db.execute_read("SELECT * FROM containers")
    return {"containers": containers}

@app.get("/metrics/invocations")
def list_invocations():
    return {"invocations": db.execute_read("SELECT * FROM invocations")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
