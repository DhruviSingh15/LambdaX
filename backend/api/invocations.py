import time
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import db
from backend.containers.pool_manager import pool_manager

router = APIRouter()

class FunctionConfig(BaseModel):
    name: str
    image: str
    memory_mb: int = 128
    sla_ms: int = 1000
    max_containers: int = 5
    max_warm_containers: int = 2
    idle_timeout_seconds: int = 300
    scheduling_policy: str = "reactive"
    min_containers: int = 0
    queue_threshold: int = 0

class InvokeRequest(BaseModel):
    payload: dict = {}

def _now():
    return datetime.utcnow().isoformat()

@router.post("/functions/register")
def register_function(config: FunctionConfig):
    func_id = str(uuid.uuid4())
    try:
        db.execute_write(
            "INSERT INTO functions (id, name, image, memory_mb, sla_ms, max_containers, max_warm_containers, idle_timeout_seconds, scheduling_policy, min_containers, queue_threshold, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (func_id, config.name, config.image, config.memory_mb, config.sla_ms, config.max_containers, config.max_warm_containers, config.idle_timeout_seconds, config.scheduling_policy, config.min_containers, config.queue_threshold, _now())
        )
    except Exception as e:
        # If it already exists, update it
        func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (config.name,))
        if func:
            func_id = func['id']
            db.execute_write(
                "UPDATE functions SET max_containers=?, max_warm_containers=?, idle_timeout_seconds=?, scheduling_policy=?, min_containers=?, queue_threshold=? WHERE id=?",
                (config.max_containers, config.max_warm_containers, config.idle_timeout_seconds, config.scheduling_policy, config.min_containers, config.queue_threshold, func_id)
            )
        else:
             raise HTTPException(status_code=400, detail=f"Database error: {e}")
             
    # Trigger pool manager to handle prewarming if policy is fixed
    pool_manager.apply_policy(config.name)
             
    return {"status": "registered", "function_id": func_id}

@router.get("/functions")
def list_functions():
    return {"functions": db.execute_read("SELECT * FROM functions")}

@router.post("/functions/{name}/invoke")
def invoke_function(name: str, request: InvokeRequest):
    func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (name,))
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")
        
    invocation_id = str(uuid.uuid4())
    queue_enter = time.time()
    
    # 1. Pool Allocation (might wait if pool is full)
    try:
        allocation = pool_manager.allocate_container(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    queue_exit = time.time()
    queue_time_ms = allocation["queue_time_ms"]
    container = allocation["container"]
    cold_start = allocation["cold_start"]
    
    # We estimate startup time based on whether it was a cold start
    startup_time_ms = queue_time_ms if cold_start else 0
    
    # 2. Execution
    exec_start = time.time()
    success = pool_manager.execute(container)
    exec_end = time.time()
    
    execution_time_ms = (exec_end - exec_start) * 1000
    
    # 3. Release Container
    pool_manager.release_container(container['id'], name)
    
    total_latency_ms = (exec_end - queue_enter) * 1000
    sla_met = total_latency_ms <= func['sla_ms']
    
    # 4. Record Invocation Telemetry in SQLite
    status = "success" if success else "error"
    db.execute_write(
        "INSERT INTO invocations (id, function_id, container_id, timestamp, queue_entered_at, queue_exit_at, queue_time_ms, cold_start, startup_time_ms, execution_time_ms, total_latency_ms, sla_ms, sla_met, status, scheduling_policy) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            invocation_id, 
            func['id'], 
            container['container_id'], 
            _now(), 
            datetime.utcfromtimestamp(queue_enter).isoformat(), 
            datetime.utcfromtimestamp(queue_exit).isoformat(), 
            queue_time_ms, 
            cold_start, 
            startup_time_ms, 
            execution_time_ms, 
            total_latency_ms, 
            func['sla_ms'], 
            sla_met, 
            status,
            func['scheduling_policy']
        )
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Function execution failed inside container")
        
    return {
        "status": "success",
        "cold_start": cold_start,
        "queue_time_ms": queue_time_ms,
        "execution_time_ms": execution_time_ms,
        "total_latency_ms": total_latency_ms,
        "container_id": container['container_id'][:12]
    }
