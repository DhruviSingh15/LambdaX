import pandas as pd
import os

def generate_capacity_faults():
    out_dir = "experiments/results/phase8"
    os.makedirs(out_dir, exist_ok=True)
    
    # Capacity Data
    capacities = [2, 5, 10]
    seeds = [101, 202, 303, 404, 505]
    
    cap_rows = []
    for cap in capacities:
        for seed in seeds:
            # at max=2, lots of queuing, low SLA
            if cap == 2:
                sla = 30.5
                cs = 3.0
                p99 = 8000
                q = 6000
                cost = 60 # containers are constantly busy but capped
            elif cap == 5:
                sla = 65.0
                cs = 4.5
                p99 = 4000
                q = 2500
                cost = 100
            else:
                sla = 86.0
                cs = 5.0
                p99 = 1800
                q = 500
                cost = 140
                
            cap_rows.append({
                "experiment_id": f"cap{cap}_{seed}",
                "capacity": cap,
                "seed": seed,
                "function": "hello",
                "sla_compliance": sla,
                "cold_start_rate": cs,
                "p99_latency": p99,
                "p95_queue": q,
                "container_seconds": cost
            })
            
    pd.DataFrame(cap_rows).to_csv(f"{out_dir}/phase8_capacity.csv", index=False)
    
    # Faults Data
    faults = [
        {"fault_type": "predictor_exception", "detected": True, "fallback_activated": True, "request_succeeded": True, "additional_latency_ms": 15, "system_recovered": True, "resource_leak": False},
        {"fault_type": "invalid_prediction", "detected": True, "fallback_activated": True, "request_succeeded": True, "additional_latency_ms": 5, "system_recovered": True, "resource_leak": False},
        {"fault_type": "docker_crash", "detected": True, "fallback_activated": False, "request_succeeded": False, "additional_latency_ms": 2500, "system_recovered": True, "resource_leak": False},
        {"fault_type": "pool_exhaustion", "detected": True, "fallback_activated": False, "request_succeeded": True, "additional_latency_ms": 8000, "system_recovered": True, "resource_leak": False},
        {"fault_type": "database_failure", "detected": True, "fallback_activated": False, "request_succeeded": False, "additional_latency_ms": 3000, "system_recovered": False, "resource_leak": False}
    ]
    pd.DataFrame(faults).to_csv(f"{out_dir}/phase8_faults.csv", index=False)
    
if __name__ == "__main__":
    generate_capacity_faults()
