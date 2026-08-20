import json
import os

class CostModel:
    def __init__(self, config_path: str = "backend/scheduler/adaptive/config.json"):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict:
        default_config = {
            "sla_violation_penalty": 100.0,
            "container_second_cost": 0.001,
            "memory_weight_per_mb": 0.001
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("cost_model", default_config)
            except Exception:
                pass
        return default_config

    def estimate_cost(self, container_seconds: float, memory_mb: int) -> float:
        """
        Normalized cost model.
        Cost = ContainerSeconds * (MemoryMB * MemoryWeight) * ContainerSecondCost
        """
        mem_weight = self.config.get("memory_weight_per_mb", 0.001)
        base_cost = self.config.get("container_second_cost", 0.001)
        return container_seconds * memory_mb * mem_weight * base_cost

    def evaluate_tradeoff(self, memory_mb: int, expected_wait_ms: float, sla_margin_ms: float, cold_start_penalty_ms: float, priority: float = 1.0) -> str:
        """
        Compare Prewarm now vs Pay cold-start latency later.
        Returns "PREWARM" or "DO_NOT_PREWARM" based on cost.
        """
        prewarm_cost = self.estimate_cost(10.0, memory_mb)
        
        # Scale the penalty by priority. 
        # Low priority (e.g., 0.1) -> small penalty -> DO_NOT_PREWARM (wait in queue)
        # High priority (e.g., 2.0) -> huge penalty -> PREWARM (scale up)
        sla_penalty = self.config.get("sla_violation_penalty", 100.0) * priority
        
        if sla_margin_ms < (cold_start_penalty_ms * 0.5):
            if sla_penalty > prewarm_cost:
                return "PREWARM"
                
        return "DO_NOT_PREWARM"
