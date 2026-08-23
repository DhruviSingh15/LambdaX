import time
from typing import Dict, Any

from backend.scheduler.base_policy import SchedulingPolicy
from backend.prediction.predictor_manager import PredictorManager
from backend.prediction.ml.hybrid_predictor import HybridPredictor
from backend.scheduler.mpc.mpc_config import MPCConfig
from backend.scheduler.mpc.mpc_state import MPCState
from backend.scheduler.mpc.mpc_controller import MPCController
from backend.scheduler.adaptive.action import DecisionAction

class MPCPolicy(SchedulingPolicy):
    def __init__(self, predictor=None):
        if predictor is None:
            # MPC uses the same hybrid predictor to remain a fair baseline
            predictor = HybridPredictor()
            
        self.predictor_manager = PredictorManager(predictor=predictor)
        self.config = MPCConfig.load_from_file()
        self.controller = MPCController(self.config)
        self.last_run = 0
        
    def on_request_arrival(self, func: Dict[str, Any], queue_length: int, pool_manager) -> bool:
        """
        Record the request for future forecasting.
        Return True to allow reactive allocation if no containers exist.
        """
        self.predictor_manager.record_request(func['id'])
        return True
        
    def on_background_monitor(self, func: Dict[str, Any], pool_manager):
        """
        Runs the MPC algorithm on an interval.
        """
        now = time.time()
        # Only run MPC on its defined step interval
        if now - self.last_run < self.config.step_seconds:
            return
            
        self.last_run = now
        func_id = func['id']
        
        # 1. Fetch Forecast
        # We need horizon steps of prediction.
        history = self.predictor_manager._get_recent_rps_history(func_id)
        predicted_demand = []
        try:
            for h in range(1, self.config.horizon + 1):
                # We assume predictor.predict returns a single value for step h if horizon is provided
                # For HybridPredictor, predict(horizon=h) returns the specific step forecast
                pred = self.predictor_manager.predictor.predict(history, horizon=h)
                predicted_demand.append(pred)
        except Exception as e:
            # Fallback
            predicted_demand = [0.0] * self.config.horizon
            print(f"[MPCPolicy] Prediction fallback triggered: {e}")
            
        # 2. Build State
        current_warm = pool_manager.get_valid_container_count(func_id)
        busy_containers = pool_manager.get_busy_container_count(func_id)
        queued_requests = pool_manager.get_queue_length(func_id)
        max_containers = func.get('max_containers', 5)
        sla_target = func.get('sla_ms', 1000)
        
        # We assume 100ms execution latency for simple math if we don't have historicals
        # (LambdaX default for this benchmark)
        estimated_exec = 100.0
        
        state = MPCState(
            current_time=now,
            warm_containers=current_warm,
            busy_containers=busy_containers,
            queued_requests=queued_requests,
            max_containers=max_containers,
            predicted_demand=predicted_demand,
            estimated_start_latency=2000.0,
            estimated_execution_latency=estimated_exec,
            sla_target=sla_target
        )
        
        # 3. Optimize Action
        decision = self.controller.optimize_action(state)
        
        # 4. Execute Action
        if decision.action == DecisionAction.PREWARM:
            shortage = decision.target_containers - current_warm
            if shortage > 0:
                for _ in range(shortage):
                    pool_manager.provision_async(func_id)
                    
        # Note: RECLAIM action is handled passively via can_reap() hook.
        # If MPC wanted to reclaim, we'll let can_reap handle it on the next sweep.

    def can_reap(self, func: Dict[str, Any], container_record: Dict[str, Any], current_pool_size: int, pool_manager=None) -> bool:
        """
        Check if we should reap this idle container.
        We run a quick 1-step MPC check to see if target < current_pool_size.
        """
        func_id = func['id']
        history = self.predictor_manager._get_recent_rps_history(func_id)
        
        try:
            predicted_demand = [self.predictor_manager.predictor.predict(history, horizon=1)]
        except Exception:
            predicted_demand = [0.0]
            
        busy_containers = pool_manager.get_busy_container_count(func_id) if pool_manager else 0
        queued_requests = pool_manager.get_queue_length(func_id) if pool_manager else 0
        
        state = MPCState(
            current_time=time.time(),
            warm_containers=current_pool_size,
            busy_containers=busy_containers,
            queued_requests=queued_requests,
            max_containers=func.get('max_containers', 5),
            predicted_demand=predicted_demand + [0.0] * (self.config.horizon - 1),
            estimated_start_latency=2000.0,
            estimated_execution_latency=100.0,
            sla_target=func.get('sla_ms', 1000)
        )
        
        decision = self.controller.optimize_action(state)
        
        if decision.action == DecisionAction.RECLAIM:
            # Safe to reap one
            return True
            
        return False
