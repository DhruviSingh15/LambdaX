import pytest
import time
from backend.scheduler.mpc.mpc_policy import MPCPolicy
from backend.scheduler.mpc.mpc_config import MPCConfig
from backend.scheduler.mpc.mpc_state import MPCState
from backend.scheduler.adaptive.action import DecisionAction
from backend.prediction.base_predictor import BasePredictor

class MockPredictor(BasePredictor):
    def __init__(self, forecast_sequence):
        super().__init__("mock")
        self.forecast_sequence = forecast_sequence
        
    def fit(self, data): pass
    def update(self, obs): pass
    def predict(self, history, horizon):
        if horizon - 1 < len(self.forecast_sequence):
            return self.forecast_sequence[horizon - 1]
        return 0.0

class CrashingPredictor(BasePredictor):
    def __init__(self): super().__init__("crashing")
    def fit(self, data): pass
    def update(self, obs): pass
    def predict(self, history, horizon): raise Exception("Simulated Failure")

class MockPoolManager:
    def __init__(self, valid=0, busy=0, queue=0):
        self.valid = valid
        self.busy = busy
        self.queue = queue
        self.provisioned = 0
        
    def get_valid_container_count(self, func_id): return self.valid
    def get_busy_container_count(self, func_id): return self.busy
    def get_queue_length(self, func_id): return self.queue
    def provision_async(self, func_id): self.provisioned += 1

def setup_mpc(forecast_sequence, config_overrides=None):
    policy = MPCPolicy(predictor=MockPredictor(forecast_sequence))
    if config_overrides:
        for k, v in config_overrides.items():
            setattr(policy.config, k, v)
    return policy

def test_forecast_handling():
    # Test 1: Full horizon consumption
    policy = setup_mpc([50, 50, 50, 50])
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 1000}
    pool = MockPoolManager(valid=2)
    
    # We will invoke background monitor and ensure it provisions based on horizon simulation
    policy.last_run = 0 # force run
    policy.on_background_monitor(func, pool)
    
    # MPC should see demand rising to 50, so it should prewarm
    assert pool.provisioned > 0

def test_capacity_enforcement():
    # Test 2: Cannot exceed max_containers
    policy = setup_mpc([20, 20, 20, 20])
    func = {'id': 'test', 'max_containers': 5, 'sla_ms': 1000}
    pool = MockPoolManager(valid=5)
    
    policy.last_run = 0
    policy.on_background_monitor(func, pool)
    
    # Should not provision any more because we are at max capacity
    assert pool.provisioned == 0

def test_cost_preference():
    # Test 3: Cost preference
    # SLA margin is large (sla=5000ms), demand is moderate
    # MPC should avoid unnecessary prewarming to save cost
    policy = setup_mpc([2, 2, 2, 2], {'cost_weight': 10.0, 'sla_weight': 1.0})
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 5000}
    pool = MockPoolManager(valid=2)
    
    policy.last_run = 0
    policy.on_background_monitor(func, pool)
    
    assert pool.provisioned == 0 # It should maintain 2, not prewarm

def test_sla_preference():
    # Test 4: SLA preference
    # SLA target is extremely tight, penalty weight is huge
    policy = setup_mpc([50, 50, 50, 50], {'cost_weight': 1.0, 'sla_weight': 1000.0})
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 10}
    pool = MockPoolManager(valid=2)
    
    policy.last_run = 0
    policy.on_background_monitor(func, pool)
    
    assert pool.provisioned > 0 # Must prewarm to avoid massive SLA penalty

def test_reclamation_dropping_demand():
    # Test 5: Reclamation logic
    policy = setup_mpc([0.1, 0.1, 0.1, 0.1], {'cost_weight': 10.0})
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 1000}
    
    can_reap = policy.can_reap(func, {}, current_pool_size=5, pool_manager=MockPoolManager(busy=0))
    # It should decide to reap because target will be < 5
    print(f"can_reap={can_reap}")
    assert can_reap == True

def test_busy_protection():
    # Test 6: Busy protection
    policy = setup_mpc([0.1, 0.1, 0.1, 0.1], {'cost_weight': 10.0})
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 1000}
    
    # 5 valid, but all 5 are busy. It cannot reclaim busy containers.
    # In MPCPolicy can_reap, if decision target is max(busy, ...), target will be 5.
    can_reap = policy.can_reap(func, {}, current_pool_size=5, pool_manager=MockPoolManager(busy=5))
    
    # Should not reap if it would drop below busy count
    assert can_reap == False

def test_prediction_failure():
    # Test 7: Prediction failure
    policy = MPCPolicy(predictor=CrashingPredictor())
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 1000}
    pool = MockPoolManager(valid=2)
    
    policy.last_run = 0
    # Should not crash, should fallback to 0 demand and do nothing
    policy.on_background_monitor(func, pool)
    
    assert pool.provisioned == 0

def test_resource_safety():
    # Test 8: Resource safety (no negative containers)
    policy = setup_mpc([0, 0, 0, 0])
    func = {'id': 'test', 'max_containers': 10, 'sla_ms': 1000}
    
    # Even with 0 containers, it shouldn't try to reclaim below 0
    can_reap = policy.can_reap(func, {}, current_pool_size=0, pool_manager=MockPoolManager(busy=0))
    assert can_reap == False
