import asyncio
import aiohttp
import time
from workloads.patterns import WorkloadPattern

class WorkloadGenerator:
    def __init__(self, target_url: str, function_name: str):
        self.target_url = target_url
        self.function_name = function_name
        self.invoke_url = f"{self.target_url}/functions/{self.function_name}/invoke"

    async def _send_request(self, session: aiohttp.ClientSession):
        """Fires a single request asynchronously and returns the response."""
        try:
            async with session.post(self.invoke_url, json={"payload": {}}) as response:
                return await response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def generate(self, pattern: WorkloadPattern):
        """Executes the workload according to the given pattern."""
        print(f"Starting workload generator for {self.function_name}...")
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time >= pattern.duration_seconds:
                    break
                
                rps = pattern.get_requests_per_second(elapsed_time)
                
                # Fire RPS requests concurrently for this exact second
                tasks = []
                for _ in range(rps):
                    tasks.append(asyncio.create_task(self._send_request(session)))
                    
                if tasks:
                    await asyncio.gather(*tasks)
                
                # Wait for the next second to tick
                # We calculate how much time passed during request firing to sleep accurately
                next_tick = (time.time() - start_time) % 1.0
                await asyncio.sleep(1.0 - next_tick)
                
        print("Workload generation complete.")
