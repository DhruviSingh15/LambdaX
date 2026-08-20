import asyncio
import json
import argparse
import sys
import os

# Ensure the parent directory is in PYTHONPATH so we can import workloads
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workloads.patterns import ConstantWorkload, BurstyWorkload, PeriodicWorkload, PoissonWorkload
from workloads.generator import WorkloadGenerator

def create_pattern(duration: int, pattern_config: dict):
    pattern_type = pattern_config.get("type", "constant")
    
    if pattern_type == "constant":
        rps = pattern_config.get("rps", 1)
        print(f"  Pattern: Constant, {rps} RPS")
        return ConstantWorkload(duration_seconds=duration, rps=rps)
        
    elif pattern_type == "bursty":
        baseline_rps = pattern_config.get("baseline_rps", 5)
        burst_rps = pattern_config.get("burst_rps", 50)
        burst_duration_seconds = pattern_config.get("burst_duration_seconds", 5)
        burst_interval_seconds = pattern_config.get("burst_interval_seconds", 10)
        print(f"  Pattern: Bursty, baseline {baseline_rps} RPS, bursts to {burst_rps} RPS every {burst_interval_seconds}s for {burst_duration_seconds}s")
        return BurstyWorkload(
            duration_seconds=duration,
            baseline_rps=baseline_rps,
            burst_rps=burst_rps,
            burst_duration_seconds=burst_duration_seconds,
            burst_interval_seconds=burst_interval_seconds
        )
        
    elif pattern_type == "periodic":
        min_rps = pattern_config.get("min_rps", 5)
        max_rps = pattern_config.get("max_rps", 20)
        period_seconds = pattern_config.get("period_seconds", 10)
        print(f"  Pattern: Periodic, oscillates between {min_rps} and {max_rps} RPS every {period_seconds}s")
        return PeriodicWorkload(
            duration_seconds=duration,
            min_rps=min_rps,
            max_rps=max_rps,
            period_seconds=period_seconds
        )
        
    elif pattern_type == "poisson":
        lam = pattern_config.get("lambda", 5)
        print(f"  Pattern: Poisson, lambda (average RPS) = {lam}")
        return PoissonWorkload(
            duration_seconds=duration,
            lam=lam
        )
        
    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")

async def main():
    parser = argparse.ArgumentParser(description="LambdaX Workload Runner")
    parser.add_argument("config_file", type=str, help="Path to the JSON experiment config file")
    parser.add_argument("--seed", type=int, help="Random seed for repeatable workloads", default=None)
    args = parser.parse_args()

    if args.seed is not None:
        import random
        random.seed(args.seed)
        print(f"Setting random seed to {args.seed}")

    try:
        with open(args.config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    target_url = config.get("target_url", "http://127.0.0.1:8000")
    
    # Check if this is a mixed workload configuration or a single workload configuration
    workload_configs = []
    
    if "workloads" in config:
        print(f"Running Mixed Workload Experiment: {config.get('experiment_id', 'unknown')}")
        workload_configs = config["workloads"]
    else:
        print(f"Running Single Workload Experiment: {config.get('experiment_id', 'unknown')}")
        workload_configs = [config]

    tasks = []
    for i, w_config in enumerate(workload_configs):
        function_name = w_config.get("function_name", "hello")
        duration = w_config.get("duration_seconds", 10)
        pattern_config = w_config.get("pattern", {})
        
        print(f"\nInitializing Workload {i+1} for function '{function_name}' ({duration}s):")
        pattern = create_pattern(duration, pattern_config)
        generator = WorkloadGenerator(target_url=target_url, function_name=function_name)
        
        tasks.append(generator.generate(pattern))
        
    print("\nStarting all workloads concurrently...\n")
    await asyncio.gather(*tasks)
    print("\nAll workloads finished.")

if __name__ == "__main__":
    asyncio.run(main())
