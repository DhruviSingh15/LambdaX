import time
import json

def handle():
    return {"message": "Hello from LambdaX!"}

if __name__ == "__main__":
    # Simulate some work
    time.sleep(0.1)
    result = handle()
    print(json.dumps(result))
