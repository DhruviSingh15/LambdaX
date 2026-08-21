import sys
import sqlite3
import numpy as np
from datetime import datetime
def generate_csv(exp_id, policy, wl, seed, rep):
    db_path = "lambdax.db"
    
    # We will compute the basic metrics from the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all distinct function IDs
    cursor.execute("SELECT DISTINCT function_id FROM invocations")
    func_ids = [r[0] for r in cursor.fetchall()]
    
    for fid in func_ids:
        cursor.execute("SELECT name, sla_ms FROM functions WHERE id=?", (fid,))
        f_row = cursor.fetchone()
        if not f_row:
            continue
        func_name, sla_ms = f_row
        
        # Get invocations
        cursor.execute("SELECT execution_time_ms, queue_time_ms, cold_start FROM invocations WHERE function_id=?", (fid,))
        invocations = cursor.fetchall()
        
        if not invocations:
            continue
            
        inv_count = len(invocations)
        cold_starts = sum(1 for r in invocations if r[2] == 1)
        cs_rate = (cold_starts / inv_count) * 100.0 if inv_count > 0 else 0.0
        
        # Latencies
        total_latencies = [(r[0] + r[1]) for r in invocations if r[0] is not None and r[1] is not None]
        queue_times = [r[1] for r in invocations if r[1] is not None]
        
        if total_latencies:
            p50_lat = np.percentile(total_latencies, 50)
            p95_lat = np.percentile(total_latencies, 95)
            p99_lat = np.percentile(total_latencies, 99)
            sla_violations = sum(1 for lat in total_latencies if lat > sla_ms)
            sla_compliance = 100.0 * (1.0 - (sla_violations / len(total_latencies)))
        else:
            p50_lat, p95_lat, p99_lat, sla_compliance = 0, 0, 0, 0
            
        if queue_times:
            p95_queue = np.percentile(queue_times, 95)
        else:
            p95_queue = 0
            
        # Container seconds
        # Aggregate active container time
        cursor.execute("SELECT container_id, MIN(timestamp), MAX(timestamp) FROM invocations WHERE function_id=? GROUP BY container_id", (fid,))
        c_stats = cursor.fetchall()
        
        # Estimate: each container is held for 10s idle + diff. 
        # For simplicity in this mock aggregator, we will just use max(start_time) - min(start_time) + 10s
        cost_s = 0
        for row in c_stats:
            min_t_str, max_t_str = row[1], row[2]
            if min_t_str and max_t_str:
                min_t = datetime.fromisoformat(min_t_str).timestamp()
                max_t = datetime.fromisoformat(max_t_str).timestamp()
                cost_s += (max_t - min_t) + 10.0
        
        print(f"{exp_id},{policy},{wl},{seed},{rep},{func_name},{sla_compliance:.2f},{cs_rate:.2f},{p50_lat:.2f},{p95_lat:.2f},{p99_lat:.2f},{p95_queue:.2f},{cost_s:.2f},{inv_count}")

if __name__ == "__main__":
    generate_csv(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
