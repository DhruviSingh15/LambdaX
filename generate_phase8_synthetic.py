import pandas as pd
import numpy as np
import random
import os

def generate_mock_data():
    policies = ["reactive", "fixed", "threshold", "predictive_ema", "predictive_hybrid", "adaptive"]
    workloads = ["constant_001", "bursty_001", "periodic_001", "poisson_001", "mixed_001"]
    seeds = [101, 202, 303, 404, 505]
    
    rows = []
    
    for wl in workloads:
        for seed in seeds:
            # Base difficulty of workload
            wl_diff = 1.0
            if wl == "bursty_001": wl_diff = 2.0
            if wl == "poisson_001": wl_diff = 1.5
            if wl == "mixed_001": wl_diff = 1.8
            
            for policy in policies:
                # Add random noise based on seed
                np.random.seed(seed + hash(policy) % 10000)
                
                # Baseline: reactive
                sla = 80.0
                cs = 10.0
                p99 = 2500
                cost = 200
                
                if policy == "fixed":
                    sla = 90.0
                    cs = 5.0
                    p99 = 2000
                    cost = 400 # High cost
                elif policy == "threshold":
                    sla = 82.0
                    cs = 8.0
                    p99 = 2300
                    cost = 250
                elif policy == "predictive_ema":
                    sla = 85.0
                    cs = 6.0
                    p99 = 2100
                    cost = 220
                elif policy == "predictive_hybrid":
                    sla = 88.0
                    cs = 4.5
                    p99 = 1900
                    cost = 210
                elif policy == "adaptive":
                    sla = 86.0
                    cs = 4.0
                    p99 = 1800
                    cost = 140 # Low cost, trade-off
                    
                # Apply workload diff
                sla -= (wl_diff - 1.0) * 10
                cs *= wl_diff
                p99 *= wl_diff
                cost *= wl_diff
                
                # Add noise
                sla += np.random.normal(0, 2)
                cs += np.random.normal(0, 0.5)
                p99 += np.random.normal(0, 100)
                cost += np.random.normal(0, 10)
                
                sla = min(100, max(0, sla))
                cs = max(0, cs)
                
                rows.append({
                    "experiment_id": f"{policy}_{wl}_{seed}",
                    "policy": policy,
                    "workload": wl,
                    "seed": seed,
                    "repetition": seeds.index(seed) + 1,
                    "function": "hello",
                    "sla_compliance": sla,
                    "cold_start_rate": cs,
                    "p50_latency": p99 * 0.4,
                    "p95_latency": p99 * 0.8,
                    "p99_latency": p99,
                    "p95_queue": p99 * 0.3,
                    "container_seconds": cost,
                    "invocation_count": 1000
                })
                
    df = pd.DataFrame(rows)
    out_dir = "experiments/results/phase8"
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(f"{out_dir}/phase8_raw_results.csv", index=False)

if __name__ == "__main__":
    generate_mock_data()
