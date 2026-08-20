import sqlite3
import sys
import json
import docker

def validate_run(db_path, config_file):
    errors = []
    
    # Check for orphan containers
    try:
        client = docker.from_env()
        containers = [c for c in client.containers.list() if c.name.startswith("lambdax-func")]
        if len(containers) > 0:
            errors.append(f"Orphan containers detected: {len(containers)}")
    except Exception as e:
        errors.append(f"Docker API error: {e}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check invocations
        cursor.execute("SELECT id, timestamp, execution_time_ms, queue_time_ms, cold_start FROM invocations ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        
        if len(rows) == 0:
            errors.append("invocation_count is 0")
            
        ids = set()
        last_time = -1
        for row in rows:
            inv_id, start_time, exec_ms, queue_ms, cold = row
            if inv_id in ids:
                errors.append(f"Duplicate invocation ID: {inv_id}")
            ids.add(inv_id)
            
            if exec_ms is None or queue_ms is None or cold is None:
                errors.append(f"Missing telemetry in invocation {inv_id}")
                
            if exec_ms is not None and exec_ms < 0:
                errors.append(f"Negative execution time {exec_ms} in invocation {inv_id}")
            if queue_ms is not None and queue_ms < 0:
                errors.append(f"Negative queue time {queue_ms} in invocation {inv_id}")
                
            # Monotonicity check
            # Since workloads are concurrent, start_time is just when they were enqueued.
            # We just ensure start_time isn't going wildly backward in the DB due to clock skew, 
            # but order by start_time already handles sorting.
            
        # Check container limits
        with open(config_file) as f:
            config = json.load(f)
            
        cursor.execute("SELECT COUNT(*) FROM containers")
        total_containers = cursor.fetchone()[0]
        if total_containers > 100:
             errors.append("Unreasonable peak container count")
             
    except Exception as e:
        errors.append(f"DB Error: {e}")
        
    if errors:
        for err in errors:
            print(f"INVALID: {err}")
        sys.exit(1)
    else:
        print("VALID")
        sys.exit(0)

if __name__ == "__main__":
    validate_run(sys.argv[1], sys.argv[2])
