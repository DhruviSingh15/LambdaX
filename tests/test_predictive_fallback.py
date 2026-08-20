import requests
import time
import subprocess
import os

API_URL = "http://127.0.0.1:8000"

def wait_for_server():
    for _ in range(10):
        try:
            r = requests.get(f"{API_URL}/health")
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def run_tests():
    if os.path.exists("lambdax.db"):
        os.remove("lambdax.db")

    print("Starting FastAPI server for fallback tests...")
    server_process = subprocess.Popen(
        [r".\venv\Scripts\python.exe", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    
    try:
        if not wait_for_server():
            print("Server failed to start.")
            return

        print("Registering test functions...")
        policies = {
            "test_crashing": "func_crashing",
            "test_invalid": "func_invalid",
            "test_zero": "func_zero"
        }
        
        for policy, func_name in policies.items():
            res = requests.post(f"{API_URL}/functions/register", json={
                "name": func_name,
                "image": "lambdax-hello:latest",
                "max_containers": 3,
                "scheduling_policy": policy,
                "idle_timeout_seconds": 30
            })
            assert res.status_code == 200, f"Failed to register {func_name}"

        # Wait for 2 seconds to let the background monitor execute (and potentially crash)
        print("Waiting 2 seconds to trigger background monitor...")
        time.sleep(2)
        
        # Verify server is still alive
        res = requests.get(f"{API_URL}/health")
        assert res.status_code == 200, "Server crashed due to background monitor exception!"
        print("PASS: Background prediction exception did not crash server.")

        for policy, func_name in policies.items():
            print(f"Testing {policy} fallback...")
            res = requests.post(f"{API_URL}/functions/{func_name}/invoke", json={})
            assert res.status_code == 200, f"Request failed for {policy}: {res.text}"
            data = res.json()
            assert data.get("status") == "success"
            print(f"PASS: {policy} fallback successful, container {data.get('container_id', 'unknown')} allocated.")
            
    finally:
        print("Shutting down server...")
        server_process.kill()

if __name__ == "__main__":
    run_tests()
