import time
from backend.scheduler.adaptive.action import DecisionAction
from backend.scheduler.adaptive.decision import Decision
from backend.scheduler.adaptive.priority_engine import PriorityEngine
from backend.scheduler.adaptive.sla_engine import SLAEngine, SLAStatus
from backend.scheduler.adaptive.queue_manager import QueueManager
from backend.scheduler.adaptive.cost_model import CostModel

class DecisionEngine:
    def __init__(self):
        self.priority_engine = PriorityEngine()
        self.sla_engine = SLAEngine()
        self.queue_manager = QueueManager()
        self.cost_model = CostModel()
        
    def _load_config(self) -> dict:
        import os, json
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def evaluate_arrival(self, func: dict, current_queue_length: int, 
                         current_containers: int, idle_containers: int, 
                         predicted_demand: float) -> Decision:
        """
        Evaluates an arriving request.
        Outputs: MICRO_QUEUE, SCALE_UP, EMERGENCY_REACTIVE, or MAINTAIN_WARM (if using an idle container)
        """
        now = time.time()
        max_c = func.get("max_containers", 5)
        memory_mb = func.get("memory_mb", 128)
        sla_ms = func.get("sla_ms", 1000)

        # 1. State Analysis
        queue_info = self.queue_manager.analyze_queue(func['id'], current_queue_length)
        expected_wait = queue_info['expected_wait_ms']
        
        sla_margin, sla_status = self.sla_engine.evaluate(sla_ms, expected_wait)
        
        # Priority isn't strictly necessary for the action enum here, but could be logged or used to bump queue position
        priority = self.priority_engine.calculate_priority(func, current_queue_length, predicted_demand)
        
        config = self._load_config()
        enable_micro = config.get("enable_micro_queue", True)
        enable_priority = config.get("enable_priority", True)
        enable_cost = config.get("enable_cost_model", True)
        
        # Cold start penalty
        if enable_priority:
            cold_penalty = self.priority_engine.calculate_cold_start_penalty(func['id'])
        else:
            cold_penalty = 1000.0 # Default fixed penalty
            
        if enable_cost:
            tradeoff = self.cost_model.evaluate_tradeoff(memory_mb, expected_wait, sla_margin, cold_penalty, priority)
        else:
            tradeoff = "PREWARM" # Always provision if cost is not a factor

        # 3. Decision Logic
        if current_containers == 0:
            return Decision(
                action=DecisionAction.SCALE_UP,
                target_containers=1,
                reason="No containers exist. Must provision.",
                confidence=1.0,
                predicted_demand=predicted_demand,
                sla_margin=sla_margin,
                expected_wait_ms=expected_wait,
                estimated_cost=self.cost_model.estimate_cost(10.0, memory_mb),
                timestamp=now
            )
            
        if idle_containers > 0:
            return Decision(
                action=DecisionAction.MAINTAIN_WARM,
                target_containers=current_containers,
                reason="Idle container available.",
                confidence=1.0,
                predicted_demand=predicted_demand,
                sla_margin=sla_margin,
                expected_wait_ms=expected_wait,
                estimated_cost=0.0,
                timestamp=now
            )
            
        max_c = func.get("max_containers", 5)
        if current_containers >= max_c:
            return Decision(
                action=DecisionAction.MICRO_QUEUE,
                target_containers=current_containers,
                reason=f"At max capacity ({max_c}). Must queue.",
                confidence=1.0,
                predicted_demand=predicted_demand,
                sla_margin=sla_margin,
                expected_wait_ms=expected_wait,
                estimated_cost=0.0,
                timestamp=now
            )
            
        if sla_status == SLAStatus.VIOLATED:
            return Decision(
                action=DecisionAction.EMERGENCY_REACTIVE,
                target_containers=current_containers + 1,
                reason=f"SLA violated if queued (wait {expected_wait:.1f}ms). Must provision immediately.",
                confidence=0.9,
                predicted_demand=predicted_demand,
                sla_margin=sla_margin,
                expected_wait_ms=expected_wait,
                estimated_cost=self.cost_model.estimate_cost(10.0, memory_mb),
                timestamp=now
            )
            
        elif sla_status in (SLAStatus.LARGE_POSITIVE, SLAStatus.SMALL_POSITIVE):
            if tradeoff == "PREWARM" or not enable_micro:
                return Decision(
                    action=DecisionAction.SCALE_UP,
                    target_containers=current_containers + 1,
                    reason=f"SLA safe but tradeoff prefers PREWARM (or MicroQueue disabled).",
                    confidence=0.8,
                    predicted_demand=predicted_demand,
                    sla_margin=sla_margin,
                    expected_wait_ms=expected_wait,
                    estimated_cost=self.cost_model.estimate_cost(10.0, memory_mb),
                    timestamp=now
                )
            else:
                return Decision(
                    action=DecisionAction.MICRO_QUEUE,
                    target_containers=current_containers,
                    reason=f"SLA safe (margin {sla_margin:.1f}ms). Cost model prefers waiting.",
                    confidence=0.8,
                    predicted_demand=predicted_demand,
                    sla_margin=sla_margin,
                    expected_wait_ms=expected_wait,
                    estimated_cost=0.0,
                    timestamp=now
                )

        # Default fallback
        return Decision(
            action=DecisionAction.SCALE_UP,
            target_containers=current_containers + 1,
            reason="Fallback scale up",
            confidence=0.5,
            predicted_demand=predicted_demand,
            sla_margin=sla_margin,
            expected_wait_ms=expected_wait,
            estimated_cost=0.0,
            timestamp=now
        )

    def evaluate_background(self, func: dict, current_containers: int, 
                            valid_containers: int, idle_containers: int, 
                            predicted_demand: float) -> Decision:
        """
        Evaluates background monitoring state.
        Outputs: PREWARM, RECLAIM, or MAINTAIN_WARM
        """
        now = time.time()
        max_c = func.get("max_containers", 5)
        min_c = func.get("min_containers", 0)
        
        # Desired capacity is ceiling of predicted demand. (Assuming 1 container handles ~10 RPS, 
        # but in our Phase 5, capacity estimator used `ceil((lambda * E[T]) / K)`. 
        # Actually, let's just use the direct capacity requirement. If predicted is raw RPS, we need to convert to containers.
        # Let's assume CapacityEstimator logic here (or pass it in).
        # We will assume predicted_demand is already converted to desired containers for simplicity, 
        # or we do a simple `ceil` here if predicted_demand is raw RPS and service time is 100ms.
        # Let's calculate desired_containers based on 100ms service time:
        # A container handles 10 requests per second if it takes 100ms.
        # So desired = predicted_demand / 10.0
        service_time_sec = self.queue_manager.estimate_service_time(func['id']) / 1000.0
        desired_containers = int((predicted_demand * service_time_sec) + 0.999) # manual ceil
        
        desired_containers = max(min_c, min(desired_containers, max_c))
        
        if valid_containers < desired_containers:
            # We need more containers!
            shortage = desired_containers - valid_containers
            target = min(valid_containers + shortage, max_c)
            return Decision(
                action=DecisionAction.PREWARM,
                target_containers=target,
                reason=f"Predicted demand ({predicted_demand:.1f}) requires {desired_containers} containers (currently {valid_containers})",
                confidence=0.9,
                predicted_demand=predicted_demand,
                sla_margin=0.0, # Not applicable for background
                expected_wait_ms=0.0,
                estimated_cost=0.0,
                timestamp=now
            )
            
        elif idle_containers > 0 and valid_containers > desired_containers and valid_containers > min_c:
            # We have excess idle containers, and demand doesn't need them.
            # RECLAIM should be handled in `can_reap`, but we can also signal it here.
            return Decision(
                action=DecisionAction.RECLAIM,
                target_containers=desired_containers,
                reason=f"Predicted demand ({predicted_demand:.1f}) only needs {desired_containers} containers. Safely reclaiming.",
                confidence=0.8,
                predicted_demand=predicted_demand,
                sla_margin=0.0,
                expected_wait_ms=0.0,
                estimated_cost=0.0,
                timestamp=now
            )
            
        return Decision(
            action=DecisionAction.MAINTAIN_WARM,
            target_containers=valid_containers,
            reason="Capacity matches predicted demand.",
            confidence=1.0,
            predicted_demand=predicted_demand,
            sla_margin=0.0,
            expected_wait_ms=0.0,
            estimated_cost=0.0,
            timestamp=now
        )
