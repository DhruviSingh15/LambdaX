import json
import sys
import requests
import time

def register_workload_functions(config_file, policy):
    with open(config_file) as f:
        config = json.load(f)
        
    workloads = config.get("workloads", [config])
    for w in workloads:
        func_name = w.get("function_name", "hello")
        
        # default max_containers = 10, sla_ms = 1000
        payload = {
            "name": func_name,
            "image": f"lambdax-hello:latest",
            "max_containers": 10,
            "idle_timeout_seconds": 10,
            "scheduling_policy": policy,
            "min_containers": 0,
            "sla_ms": 1000
        }
        resp = requests.post("http://127.0.0.1:8000/functions/register", json=payload)
        if resp.status_code != 200:
            print(f"Failed to register {func_name}: {resp.text}")
            sys.exit(1)
            
    print("Registered functions successfully.")

if __name__ == "__main__":
    register_workload_functions(sys.argv[1], sys.argv[2])
