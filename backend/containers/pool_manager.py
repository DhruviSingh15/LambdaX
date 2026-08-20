import time
import uuid
import threading
from datetime import datetime
from backend.database import db
from backend.containers.docker_manager import docker_manager
from backend.scheduler import policy_manager

class PoolManager:
    def __init__(self):
        # We need a condition variable per function to manage waiting queues
        self.function_conditions = {}
        self.function_queues = {}
        self.lock = threading.RLock()
        
        # Start background reaper
        self.reaper_thread = threading.Thread(target=self._background_reaper, daemon=True)
        self.reaper_thread.start()

    def _get_condition(self, function_id: str):
        if function_id not in self.function_conditions:
            self.function_conditions[function_id] = threading.Condition(self.lock)
            self.function_queues[function_id] = 0
        return self.function_conditions[function_id]

    def _now(self):
        return datetime.utcnow().isoformat()
        
    def get_valid_container_count(self, function_id: str) -> int:
        cond = self._get_condition(function_id)
        with cond:
            containers = db.execute_read(
                "SELECT COUNT(*) as count FROM containers WHERE function_id = ? AND state IN ('STARTING', 'IDLE', 'BUSY')",
                (function_id,)
            )
            return containers[0]['count'] if containers else 0

    def get_container_count(self, function_id: str) -> int:
        cond = self._get_condition(function_id)
        with cond:
            containers = db.execute_read(
                "SELECT COUNT(*) as count FROM containers WHERE function_id = ? AND state != 'REMOVED'",
                (function_id,)
            )
            return containers[0]['count'] if containers else 0

    def get_idle_container_count(self, function_id: str) -> int:
        cond = self._get_condition(function_id)
        with cond:
            containers = db.execute_read(
                "SELECT COUNT(*) as count FROM containers WHERE function_id = ? AND state = 'IDLE'",
                (function_id,)
            )
            return containers[0]['count'] if containers else 0

    def get_current_queue_length(self, function_id: str) -> int:
        return self.function_queues.get(function_id, 0)
        
    def apply_policy(self, function_name: str):
        func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (function_name,))
        if not func: return
        policy = policy_manager.get_policy(func.get('scheduling_policy', 'reactive'))
        policy.on_background_monitor(func, self)
        
    def provision_async(self, function_name: str):
        threading.Thread(target=self._provision_worker, args=(function_name,), daemon=True).start()
        
    def _provision_worker(self, function_name: str):
        func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (function_name,))
        if not func: return
        func_id = func['id']
        max_containers = func['max_containers']
        
        cond = self._get_condition(func_id)
        with cond:
            current = self.get_valid_container_count(func_id)
            if current >= max_containers:
                return # Can't exceed max
                
            new_id = str(uuid.uuid4())
            db.execute_write(
                "INSERT INTO containers (id, container_id, function_id, state, created_at, started_at, last_used_at, last_state_change_at) "
                "VALUES (?, ?, ?, 'STARTING', ?, ?, ?, ?)",
                (new_id, "", func_id, self._now(), self._now(), self._now(), self._now())
            )
            
        try:
            docker_id = docker_manager.create_and_start(func['image'], function_name, func['memory_mb'])
            with cond:
                db.execute_write(
                    "UPDATE containers SET container_id = ?, state = 'IDLE', started_at = ?, last_state_change_at = ? WHERE id = ?",
                    (docker_id, self._now(), self._now(), new_id)
                )
                cond.notify()
        except Exception as e:
            with cond:
                db.execute_write("UPDATE containers SET state = 'ERROR' WHERE id = ?", (new_id,))
            print(f"Async provision failed: {e}")

    def allocate_container(self, function_name: str) -> dict:
        """
        Allocates a WARM container or provisions a NEW one if under limit.
        If at limit, waits (blocks via condition) for a container to become IDLE.
        """
        # Fetch function config
        func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (function_name,))
        if not func:
            raise ValueError(f"Function {function_name} not found")
        
        func_id = func['id']
        max_containers = func['max_containers']
        policy = policy_manager.get_policy(func.get('scheduling_policy', 'reactive'))
        
        cond = self._get_condition(func_id)
        queue_start = time.time()
        
        with cond:
            self.function_queues[func_id] += 1
            
        # Policy hook
        action = policy.on_request_arrival(func, self.function_queues[func_id], self)
        
        with cond:
            try:
                while True:
                    # 1. Lazy Cleanup
                    self._lazy_cleanup(func_id)
                    
                    # 2. Check for IDLE containers
                    idle_container = db.execute_read_one(
                        "SELECT * FROM containers WHERE function_id = ? AND state = 'IDLE' LIMIT 1",
                        (func_id,)
                    )
                    
                    if idle_container:
                        container_id = idle_container['id']
                        db.execute_write(
                            "UPDATE containers SET state = 'BUSY', last_state_change_at = ?, last_used_at = ? WHERE id = ?",
                            (self._now(), self._now(), container_id)
                        )
                        return {
                            "container": idle_container,
                            "cold_start": False,
                            "queue_time_ms": (time.time() - queue_start) * 1000
                        }
                    
                    # 3. No IDLE containers. Check if we can provision a new one.
                    current_containers = db.execute_read(
                        "SELECT * FROM containers WHERE function_id = ? AND state != 'REMOVED'",
                        (func_id,)
                    )
                    
                    if len(current_containers) < max_containers:
                        # Determine if policy explicitly wants to wait (MICRO_QUEUE)
                        # Action can be a boolean (old policies) or DecisionAction enum (adaptive)
                        should_provision = True
                        if hasattr(action, 'name'):
                            if action.name in ('MICRO_QUEUE', 'MAINTAIN_WARM'):
                                should_provision = False
                        elif action is False:
                            should_provision = False
                            
                        if should_provision:
                            # We can provision a new container
                            new_id = str(uuid.uuid4())
                            db.execute_write(
                                "INSERT INTO containers (id, container_id, function_id, state, created_at, started_at, last_used_at, last_state_change_at) "
                                "VALUES (?, ?, ?, 'STARTING', ?, ?, ?, ?)",
                                (new_id, "", func_id, self._now(), self._now(), self._now(), self._now())
                            )
                            break 
                    
                    # 4. At maximum capacity, or we deliberately chose to MICRO_QUEUE, we must WAIT
                    cond.wait(timeout=1.0) # Wake up every 1s to re-evaluate in case of race conditions

            finally:
                self.function_queues[func_id] -= 1
                
        # If we broke out of the loop, it means we need to CREATE a new container synchronously
        try:
            docker_id = docker_manager.create_and_start(func['image'], function_name, func['memory_mb'])
            
            with cond:
                db.execute_write(
                    "UPDATE containers SET container_id = ?, state = 'BUSY', started_at = ?, last_state_change_at = ? WHERE id = ?",
                    (docker_id, self._now(), self._now(), new_id)
                )
                container = db.execute_read_one("SELECT * FROM containers WHERE id = ?", (new_id,))
                
            return {
                "container": container,
                "cold_start": True,
                "queue_time_ms": (time.time() - queue_start) * 1000
            }
        except Exception as e:
            with cond:
                db.execute_write("UPDATE containers SET state = 'ERROR' WHERE id = ?", (new_id,))
            raise Exception(f"Failed to provision container: {e}")

    def release_container(self, container_record_id: str, function_name: str):
        func = db.execute_read_one("SELECT * FROM functions WHERE name = ?", (function_name,))
        if not func: return
        func_id = func['id']
        
        cond = self._get_condition(func_id)
        with cond:
            db.execute_write(
                "UPDATE containers SET state = 'IDLE', last_used_at = ?, last_state_change_at = ? WHERE id = ?",
                (self._now(), self._now(), container_record_id)
            )
            cond.notify()

    def execute(self, container: dict) -> bool:
        docker_id = container['container_id']
        return docker_manager.execute_function(docker_id)
        
    def _lazy_cleanup(self, function_id: str):
        containers = db.execute_read("SELECT * FROM containers WHERE function_id = ? AND state IN ('BUSY', 'IDLE', 'STARTING')", (function_id,))
        for c in containers:
            if c['container_id']:
                status = docker_manager.inspect_container(c['container_id'])
                if status not in ("running", "created"):
                    db.execute_write("UPDATE containers SET state = 'ERROR' WHERE id = ?", (c['id'],))

    def _background_reaper(self):
        while True:
            time.sleep(1)
            try:
                functions = db.execute_read("SELECT * FROM functions")
                for func in functions:
                    func_id = func['id']
                    timeout = func['idle_timeout_seconds']
                    policy = policy_manager.get_policy(func.get('scheduling_policy', 'reactive'))
                    
                    # Periodic policy hook
                    policy.on_background_monitor(func, self)
                    
                    cond = self._get_condition(func_id)
                    with cond:
                        current_pool_size = self.get_valid_container_count(func_id)
                        idle_containers = db.execute_read(
                            "SELECT * FROM containers WHERE function_id = ? AND state = 'IDLE'",
                            (func_id,)
                        )
                        
                        now = datetime.utcnow()
                        for c in idle_containers:
                            last_used = datetime.fromisoformat(c['last_used_at'])
                            if (now - last_used).total_seconds() > timeout:
                                if policy.can_reap(func, c, current_pool_size, self):
                                    db.execute_write("UPDATE containers SET state = 'RECLAIMING' WHERE id = ?", (c['id'],))
                                    docker_manager.remove_container(c['container_id'])
                                    db.execute_write("UPDATE containers SET state = 'REMOVED' WHERE id = ?", (c['id'],))
                                    current_pool_size -= 1
                                
            except Exception as e:
                print(f"Reaper error: {e}")

pool_manager = PoolManager()
