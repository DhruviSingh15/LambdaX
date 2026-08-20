import sqlite3
import argparse
import os

def generate_report(db_path: str):
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get functions
    cursor.execute("SELECT id, name FROM functions")
    functions = cursor.fetchall()

    for row in functions:
        func_id = row['id']
        func_name = row['name']
        print(f"\nExperiment Report: Function '{func_name}'")
        print("====================================")
        
        cursor.execute("SELECT COUNT(*) as count FROM invocations WHERE function_id = ?", (func_id,))
        total_requests = cursor.fetchone()['count']
        if total_requests == 0:
            print("No requests found in database.")
            print("====================================")
            continue

        cursor.execute("SELECT COUNT(*) as count FROM invocations WHERE function_id = ? AND cold_start = 1", (func_id,))
        cold_starts = cursor.fetchone()['count']
        warm_starts = total_requests - cold_starts

        cursor.execute("SELECT total_latency_ms, queue_time_ms FROM invocations WHERE function_id = ? ORDER BY total_latency_ms ASC", (func_id,))
        rows = cursor.fetchall()
        
        latencies = [r['total_latency_ms'] for r in rows if r['total_latency_ms'] is not None]
        queues = [r['queue_time_ms'] for r in rows if r['queue_time_ms'] is not None]
        
        def percentile(data, p):
            if not data: return 0
            idx = int(len(data) * p)
            return data[idx]

        p50 = percentile(latencies, 0.50)
        p95 = percentile(latencies, 0.95)
        p99 = percentile(latencies, 0.99)
        avg_queue = sum(queues) / len(queues) if queues else 0

        cursor.execute("SELECT COUNT(*) as count FROM invocations WHERE function_id = ? AND sla_met = 0", (func_id,))
        sla_violations = cursor.fetchone()['count']
        sla_compliance_pct = ((total_requests - sla_violations) / total_requests * 100) if total_requests > 0 else 0

        cursor.execute("SELECT * FROM containers WHERE function_id = ?", (func_id,))
        all_containers = cursor.fetchall()
        peak_containers = len(all_containers)
        reclaimed_containers = sum(1 for c in all_containers if c['state'] in ('REMOVED', 'RECLAIMING'))
        
        # Calculate container-seconds
        import datetime
        container_seconds = 0
        for c in all_containers:
            try:
                start = datetime.datetime.fromisoformat(c['started_at'])
                end = datetime.datetime.fromisoformat(c['last_state_change_at'])
                container_seconds += (end - start).total_seconds()
            except Exception:
                pass
                
        # Calculate cold start time
        cursor.execute("SELECT startup_time_ms FROM invocations WHERE function_id = ? AND cold_start = 1", (func_id,))
        cold_start_rows = cursor.fetchall()
        startup_times = [r['startup_time_ms'] for r in cold_start_rows if r['startup_time_ms'] is not None]
        avg_startup_time = sum(startup_times) / len(startup_times) if startup_times else 0

        cursor.execute("SELECT scheduling_policy FROM functions WHERE id = ?", (func_id,))
        policy = cursor.fetchone()['scheduling_policy']
        
        cold_start_rate = (cold_starts / total_requests * 100) if total_requests > 0 else 0
        p95_queue = percentile(queues, 0.95)

        print(f"Policy:               {policy.upper()}")
        print(f"Total requests:       {total_requests}")
        print(f"Cold starts:          {cold_starts} ({cold_start_rate:.2f}%)")
        print(f"Warm starts:          {warm_starts}")
        print(f"Avg startup time:     {avg_startup_time:.2f} ms")
        print(f"P50 latency:          {p50:.2f} ms")
        print(f"P95 latency:          {p95:.2f} ms")
        print(f"P99 latency:          {p99:.2f} ms")
        print(f"Average queue:        {avg_queue:.2f} ms")
        print(f"P95 queue:            {p95_queue:.2f} ms")
        print(f"SLA violations:       {sla_violations} ({sla_compliance_pct:.2f}% compliance)")
        print(f"Peak containers:      {peak_containers}")
        print(f"Containers reclaimed: {reclaimed_containers}")
        print(f"Container-seconds:    {container_seconds:.2f} s")
        print("====================================")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="lambdax.db", help="Path to sqlite DB")
    args = parser.parse_args()
    generate_report(args.db)
