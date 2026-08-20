from typing import Dict, Any
from backend.scheduler.base_policy import SchedulingPolicy
from backend.prediction.predictor_manager import PredictorManager
from backend.prediction.exponential_smoothing import ExponentialSmoothingPredictor

class PredictivePolicy(SchedulingPolicy):
    """
    Proactively pre-warms containers based on predicted incoming demand.
    Falls back to Reactive behavior if prediction fails or returns 0.
    """
    
    def __init__(self, predictor=None):
        # Default to EMA if no predictor provided
        if predictor is None:
            predictor = ExponentialSmoothingPredictor(alpha=0.5)
            
        self.predictor_manager = PredictorManager(predictor=predictor)

    def on_request_arrival(self, func: Dict[str, Any], queue_length: int, pool_manager) -> bool:
        """
        Record the request in the ring buffer, then fall back to Reactive allocation logic
        (i.e., if no container is immediately available, we must provision one on-demand).
        """
        self.predictor_manager.record_request(func['id'])
        
        # Reactive allocation: if we need a container now, we must spawn it.
        # Returning True means "Yes, attempt to provision if capacity allows".
        return True

    def on_background_monitor(self, func: Dict[str, Any], pool_manager):
        """
        Periodically predicts future demand and proactively provisions containers.
        """
        desired_containers = self.predictor_manager.get_desired_capacity(func['id'])
        
        # Bounded by max_containers
        max_c = func.get('max_containers', 5)
        desired_containers = min(desired_containers, max_c)
        
        # We also respect min_containers (if the user wants a fixed baseline)
        min_c = func.get('min_containers', 0)
        desired_containers = max(desired_containers, min_c)
        
        current_valid = pool_manager.get_valid_container_count(func['id'])
        
        if desired_containers > current_valid:
            shortage = desired_containers - current_valid
            # Proactively spawn
            for _ in range(shortage):
                # Using thread-safe async provisioning hook
                pool_manager.provision_async(func['id'])

    def can_reap(self, func: Dict[str, Any], container_record: Dict[str, Any], current_pool_size: int, pool_manager=None) -> bool:
        """
        Check if we have a surplus compared to predicted demand.
        If we have more valid containers than predicted, we can reap idle ones.
        """
        desired_containers = self.predictor_manager.get_desired_capacity(func['id'])
        
        # Never drop below min_containers
        min_c = func.get('min_containers', 0)
        desired_containers = max(desired_containers, min_c)
        
        current_valid = current_pool_size
        
        # We can reap this container if removing it still leaves us with >= desired_containers
        if current_valid > desired_containers:
            return True
            
        return False
