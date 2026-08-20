import unittest
import threading
import time
import os
from backend.containers.pool_manager import pool_manager
from backend.database import db
from backend.containers.docker_manager import docker_manager

class TestPhase7Integration(unittest.TestCase):
    def setUp(self):
        # Setup a dummy function in DB
        db.execute_write("DELETE FROM functions WHERE name = 'test_adaptive'")
        db.execute_write(
            "INSERT INTO functions (id, name, image, memory_mb, sla_ms, max_containers, min_containers, idle_timeout_seconds, scheduling_policy) "
            "VALUES ('func_adaptive_1', 'test_adaptive', 'alpine', 128, 1000, 5, 0, 10, 'adaptive')"
        )

    def test_concurrent_requests(self):
        # Test 9: Deadlock
        # Run 20 concurrent requests
        threads = []
        results = []
        
        def worker():
            try:
                # We mock or use real docker? If docker is running, this provisions real alpine containers.
                # Since this is an integration test, it will actually start containers.
                # To keep it fast, we will allocate and immediately release.
                alloc = pool_manager.allocate_container('test_adaptive')
                time.sleep(0.5) # Simulate execution
                pool_manager.release_container(alloc['container']['id'], 'test_adaptive')
                results.append(True)
            except Exception as e:
                print(f"Worker failed: {e}")
                results.append(False)
                
        for _ in range(20):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join(timeout=15.0)
            
        self.assertEqual(len(results), 20)
        self.assertTrue(all(results), "Not all workers succeeded, possible deadlock or timeout.")

        # Test 10: Resource leaks
        # DB active containers vs Docker active containers
        db_containers = db.execute_read(
            "SELECT * FROM containers WHERE function_id = 'func_adaptive_1' AND state NOT IN ('REMOVED', 'ERROR')"
        )
        
        # We don't check Docker strictly here if Docker manager has lag, but we can check DB consistency
        self.assertTrue(len(db_containers) <= 5, "Max capacity constraint violated!")
        
        for c in db_containers:
            status = docker_manager.inspect_container(c['container_id'])
            self.assertIn(status, ['running', 'created'], "DB container not in running/created state in Docker")

    def tearDown(self):
        # Cleanup
        containers = db.execute_read("SELECT * FROM containers WHERE function_id = 'func_adaptive_1' AND state != 'REMOVED'")
        for c in containers:
            try:
                docker_manager.remove_container(c['container_id'])
            except:
                pass
        db.execute_write("DELETE FROM containers WHERE function_id = 'func_adaptive_1'")
        db.execute_write("DELETE FROM functions WHERE name = 'test_adaptive'")

if __name__ == '__main__':
    unittest.main()
