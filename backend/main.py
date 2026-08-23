from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import invocations, dashboard
from backend.database import db
from backend.containers.docker_manager import docker_manager

# Initialize Database on startup
db.init_db()

app = FastAPI(title="LambdaX API (Phase 2)")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include invocation routes
app.include_router(invocations.router)
app.include_router(dashboard.router)

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
