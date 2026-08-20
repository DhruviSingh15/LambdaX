from dataclasses import dataclass
from backend.scheduler.adaptive.action import DecisionAction

@dataclass
class Decision:
    action: DecisionAction
    target_containers: int
    reason: str
    confidence: float
    predicted_demand: float
    sla_margin: float
    expected_wait_ms: float
    estimated_cost: float
    timestamp: float
