from fastapi import APIRouter
from backend.database import db
import time

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

from datetime import datetime, timedelta
    
@router.get("/overview")
def get_overview():
    now = time.time()
    cutoff_iso = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
    
    # Active containers
    containers = db.execute_read("SELECT count(*) as count FROM containers WHERE state IN ('RUNNING', 'BUSY', 'STARTING', 'WARM', 'IDLE')")
    active_containers = containers[0]['count'] if containers else 0
    
    # Queue (approximate by looking for null queue_exit_at, though typically invocations are only inserted after completion)
    queued = db.execute_read("SELECT count(*) as count FROM invocations WHERE queue_exit_at IS NULL")
    queue_size = queued[0]['count'] if queued else 0
    
    # Metrics (last 60 seconds approximation)
    invocs = db.execute_read("SELECT * FROM invocations WHERE timestamp > ?", (cutoff_iso,))
    total_invocations = len(invocs)
    rps = total_invocations / 60.0
    
    completed = [i for i in invocs if i['status'] == 'success']
    cold_starts = sum(1 for i in completed if i['cold_start'])
    cold_start_pct = (cold_starts / len(completed) * 100) if completed else 0
    
    # Mock SLA target for overview as 2000ms average
    sla_met = sum(1 for i in completed if i['total_latency_ms'] <= 2000)
    sla_compliance = (sla_met / len(completed) * 100) if completed else 0
    
    # P99 latency
    latencies = sorted([i['total_latency_ms'] for i in completed])
    p99_latency = latencies[int(len(latencies)*0.99)] if len(latencies) > 0 else 0
    
    # Recent decisions
    decisions = db.execute_read("SELECT * FROM scheduler_decisions ORDER BY timestamp DESC LIMIT 10")
    
    return {
        "rps": round(rps, 1),
        "active_containers": active_containers,
        "queue_size": queue_size,
        "cold_start_pct": round(cold_start_pct, 1),
        "sla_compliance": round(sla_compliance, 1),
        "p99_latency": round(p99_latency, 1),
        "recent_decisions": decisions
    }

@router.get("/functions")
def get_functions():
    funcs = db.execute_read("SELECT * FROM functions")
    result = []
    cutoff_iso = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
    for f in funcs:
        func_id = f['id']  # invocations table uses the UUID function_id
        invocs = db.execute_read("SELECT * FROM invocations WHERE function_id = ? AND timestamp > ?", (func_id, cutoff_iso))
        total = len(invocs)
        completed = [i for i in invocs if i['status'] == 'success']
        
        rps = total / 60.0
        cold_starts = sum(1 for i in completed if i['cold_start'])
        cs_pct = (cold_starts / len(completed) * 100) if completed else 0
        
        latencies = sorted([i['total_latency_ms'] for i in completed])
        p50 = latencies[int(len(latencies)*0.5)] if len(latencies) > 0 else 0
        p99 = latencies[int(len(latencies)*0.99)] if len(latencies) > 0 else 0
        
        sla = f['sla_ms']
        sla_met = sum(1 for l in latencies if l <= sla)
        sla_pct = (sla_met / len(completed) * 100) if completed else 0
        
        # Lifecycle simulation (last 10 requests)
        recent_invocs = db.execute_read("SELECT * FROM invocations WHERE function_id = ? ORDER BY timestamp DESC LIMIT 10", (func_id,))
        
        result.append({
            "id": f['name'],  # UI expects the human-readable name here
            "rps": round(rps, 1),
            "p50_ms": round(p50, 1),
            "p99_ms": round(p99, 1),
            "sla_pct": round(sla_pct, 1),
            "cold_start_pct": round(cs_pct, 1),
            "sla_target_ms": sla,
            "status": "Healthy" if sla_pct >= 90 else "Warning",
            "recent_requests": recent_invocs
        })
    return result

@router.get("/containers")
def get_containers():
    return db.execute_read("SELECT * FROM containers WHERE state != 'REMOVED' ORDER BY created_at DESC")

@router.get("/scheduler")
def get_scheduler():
    decisions = db.execute_read("SELECT * FROM scheduler_decisions ORDER BY timestamp DESC LIMIT 1")
    if not decisions:
        return {}
    dec = decisions[0]
    func_id = dec["function_id"]
    
    # Get current live state for this function
    warm = db.execute_read("SELECT count(*) as count FROM containers WHERE function_id = ? AND state IN ('WARM', 'IDLE')", (func_id,))
    busy = db.execute_read("SELECT count(*) as count FROM containers WHERE function_id = ? AND state IN ('BUSY', 'RUNNING')", (func_id,))
    queued = db.execute_read("SELECT count(*) as count FROM invocations WHERE function_id = ? AND queue_exit_at IS NULL", (func_id,))
    func = db.execute_read_one("SELECT name, sla_ms FROM functions WHERE id = ?", (func_id,))
    
    from backend.scheduler.policy_manager import policy_manager
    forecast_data = policy_manager.get_last_forecast(func_id)
    
    return {
        "action": dec["action"],
        "function": func["name"] if func else func_id,
        "predicted_demand": round(dec["predicted_demand"] or 0, 1),
        "available_containers": dec["target_containers"],
        "expected_wait_ms": round(dec["expected_wait_ms"] or 0, 1),
        "sla_budget_ms": round(dec["sla_margin_ms"] or 0, 1),
        "estimated_cost": round(dec["estimated_cost"] or 0, 2) if dec["estimated_cost"] else 0,
        "reason": dec["reason"],
        "timestamp": dec["timestamp"],
        "current_state": {
            "warm_containers": warm[0]["count"] if warm else 0,
            "busy_containers": busy[0]["count"] if busy else 0,
            "queue_length": queued[0]["count"] if queued else 0,
            "sla_ms": func["sla_ms"] if func else 0,
        },
        "forecast": forecast_data["forecast"][:4] if forecast_data and forecast_data["forecast"] else []
    }

@router.get("/forecast")
def get_forecast():
    from backend.scheduler.policy_manager import policy_manager
    return policy_manager.get_last_forecast()

import os
import csv
@router.get("/experiments")
def get_experiments():
    summary_path = os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "results", "phase9", "phase9_summary.csv")
    
    adaptive = {}
    mpc = {}
    
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # We will extract the burst_001 workload for comparison
                if row["workload"] == "burst_001":
                    if row["policy"] == "adaptive":
                        adaptive = row
                    elif row["policy"] == "mpc":
                        mpc = row
                        
    return {
        "status": "completed" if adaptive else "error",
        "phase9": {
            "adaptive_cost": round(float(adaptive.get("mean_cost", 0)), 2),
            "mpc_cost": round(float(mpc.get("mean_cost", 0)), 2),
            "adaptive_p99": round(float(adaptive.get("mean_p99", 0)), 1),
            "mpc_p99": round(float(mpc.get("mean_p99", 0)), 1),
            "adaptive_sla": round(float(adaptive.get("mean_sla", 0)), 1),
            "mpc_sla": round(float(mpc.get("mean_sla", 0)), 1),
            "adaptive_cs": round(float(adaptive.get("mean_cs", 0)), 2),
            "mpc_cs": round(float(mpc.get("mean_cs", 0)), 2)
        }
    }
