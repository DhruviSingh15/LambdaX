import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("Testing /health...")
    r = requests.get(f"{BASE_URL}/health")
    print(r.json())
    assert r.status_code == 200

def test_register():
    print("\nRegistering function 'hello'...")
    payload = {
        "name": "hello",
        "image": "lambdax-hello:latest",
        "memory_mb": 128,
        "sla_ms": 1000
    }
    r = requests.post(f"{BASE_URL}/functions/register", json=payload)
    print(r.json())
    assert r.status_code == 200

def test_invoke():
    print("\nInvoking 'hello' - Request #1 (Expect COLD)")
    r = requests.post(f"{BASE_URL}/functions/hello/invoke", json={"payload": {}})
    data = r.json()
    print(data)
    assert data["cold_start"] is True

    print("\nInvoking 'hello' - Request #2 (Expect WARM)")
    r = requests.post(f"{BASE_URL}/functions/hello/invoke", json={"payload": {}})
    data = r.json()
    print(data)
    assert data["cold_start"] is False

    print("\nInvoking 'hello' - Request #3 (Expect WARM)")
    r = requests.post(f"{BASE_URL}/functions/hello/invoke", json={"payload": {}})
    data = r.json()
    print(data)
    assert data["cold_start"] is False
    
def test_containers():
    print("\nListing containers...")
    r = requests.get(f"{BASE_URL}/containers")
    print(r.json())

if __name__ == "__main__":
    # Wait for server to start
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
        test_health()
        test_register()
        test_invoke()
        test_containers()
        print("\nAll tests passed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
