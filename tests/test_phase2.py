import requests
import time
import sys
import threading

BASE_URL = "http://127.0.0.1:8000"

def register_function():
    print("Registering 'hello' function with max_containers=3, idle_timeout=5...")
    payload = {
        "name": "hello",
        "image": "lambdax-hello:latest",
        "memory_mb": 128,
        "sla_ms": 1000,
        "max_containers": 3,
        "max_warm_containers": 2,
        "idle_timeout_seconds": 5
    }
    r = requests.post(f"{BASE_URL}/functions/register", json=payload)
    assert r.status_code == 200

def invoke():
    r = requests.post(f"{BASE_URL}/functions/hello/invoke", json={"payload": {}})
    return r.json()

def test_1_single_request():
    print("\n--- Test 1: Single Request ---")
    data = invoke()
    print(data)
    assert data["cold_start"] is True

def test_2_sequential_requests():
    print("\n--- Test 2: Sequential Requests (Reuse) ---")
    d1 = invoke()
    print(d1)
    assert d1["cold_start"] is False
    d2 = invoke()
    print(d2)
    assert d2["cold_start"] is False
    assert d1["container_id"] == d2["container_id"]

def test_3_concurrent_requests():
    print("\n--- Test 3: Concurrent Requests ---")
    results = []
    
    def worker():
        results.append(invoke())

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    for r in results:
        print(r)
        
    container_ids = set(r["container_id"] for r in results)
    assert len(container_ids) == 3, f"Expected 3 distinct containers, got {len(container_ids)}"
    
def test_4_maximum_capacity():
    print("\n--- Test 4: Maximum Capacity (Queueing) ---")
    results = []
    
    def worker():
        results.append(invoke())

    # Send 5 concurrent requests (max_containers=3)
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    for r in results:
        print(r)
        
    # We should still only have used 3 distinct containers
    container_ids = set(r["container_id"] for r in results)
    assert len(container_ids) == 3, f"Expected 3 distinct containers, got {len(container_ids)}"
    
    # 2 requests should have a noticeable queue_time_ms
    queued = sum(1 for r in results if r["queue_time_ms"] > 50)
    assert queued >= 2, f"Expected at least 2 requests to queue, got {queued}"

def test_5_idle_timeout():
    print("\n--- Test 5: Idle Timeout (Reaper) ---")
    print("Waiting 7 seconds for reaper to clean up IDLE containers...")
    time.sleep(7)
    
    r = requests.get(f"{BASE_URL}/containers")
    containers = r.json()["containers"]
    
    removed = [c for c in containers if c['state'] == 'REMOVED']
    print(f"Removed containers in DB: {len(removed)}")
    assert len(removed) >= 3, "Expected at least 3 containers to be reaped"

def test_6_error_recovery():
    print("\n--- Test 6: Error Recovery ---")
    # First, allocate a new container by invoking
    d1 = invoke()
    container_id = d1['container_id']
    print(f"Spawned {container_id}")
    
    # Now brutally kill it via docker
    import subprocess
    subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
    print(f"Killed docker container {container_id}")
    
    # Next invocation should detect it's missing (lazy check) or provision a new one
    d2 = invoke()
    print(d2)
    assert d2['container_id'] != container_id, "Should have provisioned a new container"

if __name__ == "__main__":
    for _ in range(10):
        try:
            requests.get(f"{BASE_URL}/health")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("Server did not start in time.")
        sys.exit(1)
        
    try:
        register_function()
        test_1_single_request()
        test_2_sequential_requests()
        test_3_concurrent_requests()
        test_4_maximum_capacity()
        test_5_idle_timeout()
        test_6_error_recovery()
        print("\nAll Phase 2 tests passed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
