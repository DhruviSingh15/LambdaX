from typing import Dict, Any
from backend.scheduler.base_policy import SchedulingPolicy
from backend.prediction.predictor_manager import PredictorManager
from backend.prediction.exponential_smoothing import ExponentialSmoothingPredictor
from backend.scheduler.adaptive.decision_engine import DecisionEngine
from backend.scheduler.adaptive.action import DecisionAction
from backend.database import db

class AdaptivePolicy(SchedulingPolicy):
    def __init__(self, predictor=None):
        if predictor is None:
            predictor = ExponentialSmoothingPredictor(alpha=0.5)
            
        self.predictor_manager = PredictorManager(predictor=predictor)
        self.decision_engine = DecisionEngine()
        self._last_predicted_demand = {}

    def _get_predicted_demand(self, func_id: int) -> float:
        # PredictorManager.get_desired_capacity usually returns an int (desired containers)
        # We can use that as a proxy for "predicted demand in containers".
        # Or if we want RPS, we might need a different method.
        # But get_desired_capacity handles the conversion. Let's just use it as our "demand" (in containers).
        return float(self.predictor_manager.get_desired_capacity(func_id))

    def _log_decision(self, func_id: int, decision) -> None:
        try:
            query = """
                INSERT INTO scheduler_decisions 
                (function_id, timestamp, action, target_containers, reason, confidence, 
                predicted_demand, sla_margin_ms, expected_wait_ms, estimated_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                func_id,
                decision.timestamp,
                decision.action.value,
                decision.target_containers,
                decision.reason,
                decision.confidence,
                decision.predicted_demand,
                decision.sla_margin,
                decision.expected_wait_ms,
                decision.estimated_cost
            )
            db.execute_write(query, params)
        except Exception as e:
            # Table might not exist yet if Phase 7.10 isn't fully migrated, ignore for now
            pass

    def on_request_arrival(self, func: Dict[str, Any], queue_length: int, pool_manager) -> Any:
        self.predictor_manager.record_request(func['id'])
        
        current_containers = pool_manager.get_container_count(func['id'])
        idle_containers = pool_manager.get_idle_container_count(func['id'])
        predicted_demand = self._get_predicted_demand(func['id'])
        
        try:
            decision = self.decision_engine.evaluate_arrival(
                func=func,
                current_queue_length=queue_length,
                current_containers=current_containers,
                idle_containers=idle_containers,
                predicted_demand=predicted_demand
            )
            
            self._log_decision(func['id'], decision)
            return decision.action
        except Exception as e:
            print(f"Adaptive decision engine failed: {e}. Falling back to EMA.")
            # Fallback to EMA
            desired_containers = self.predictor_manager.get_desired_capacity(func['id'])
            if current_containers < desired_containers:
                return DecisionAction.SCALE_UP
            else:
                return True # Fallback boolean which acts as normal reactive handling

    def on_background_monitor(self, func: Dict[str, Any], pool_manager):
        # Force a fresh prediction during background monitoring
        predicted_demand = self._get_predicted_demand(func['id'])
        self._last_predicted_demand[func['id']] = predicted_demand
        
        current_containers = pool_manager.get_container_count(func['id'])
        valid_containers = pool_manager.get_valid_container_count(func['id'])
        idle_containers = pool_manager.get_idle_container_count(func['id'])
        
        try:
            decision = self.decision_engine.evaluate_background(
                func=func,
                current_containers=current_containers,
                valid_containers=valid_containers,
                idle_containers=idle_containers,
                predicted_demand=predicted_demand
            )
            
            self._log_decision(func['id'], decision)
            
            if decision.action == DecisionAction.PREWARM:
                shortage = decision.target_containers - valid_containers
                if shortage > 0:
                    for _ in range(shortage):
                        pool_manager.provision_async(func['id'])
            
            elif decision.action == DecisionAction.RECLAIM:
                # We don't forcefully kill here; we let the reaper do it by calling can_reap
                pass
        except Exception as e:
            print(f"Adaptive background monitor failed: {e}. Falling back to EMA.")
            desired_containers = self.predictor_manager.get_desired_capacity(func['id'])
            if desired_containers > valid_containers:
                shortage = desired_containers - valid_containers
                for _ in range(min(shortage, func.get('max_containers', 5))):
                    pool_manager.provision_async(func['id'])

    def can_reap(self, func: Dict[str, Any], container_record: Dict[str, Any], current_pool_size: int, pool_manager=None) -> bool:
        # Check if protecting is needed
        predicted_demand = self._last_predicted_demand.get(func['id'], 0.0)
        valid_containers = current_pool_size
        
        try:
            decision = self.decision_engine.evaluate_background(
                func=func,
                current_containers=pool_manager.get_container_count(func['id']) if pool_manager else valid_containers,
                valid_containers=valid_containers,
                idle_containers=pool_manager.get_idle_container_count(func['id']) if pool_manager else 1,
                predicted_demand=predicted_demand
            )
            
            if decision.action == DecisionAction.RECLAIM and valid_containers > decision.target_containers:
                return True
                
            return False
        except Exception as e:
            print(f"Adaptive can_reap failed: {e}. Falling back to EMA.")
            desired_containers = self.predictor_manager.get_desired_capacity(func['id'])
            return valid_containers > desired_containers
