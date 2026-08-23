from dataclasses import dataclass
from typing import List

@dataclass
class MPCState:
    current_time: float
    warm_containers: int
    busy_containers: int
    queued_requests: int
    max_containers: int
    predicted_demand: List[float]
    estimated_start_latency: float
    estimated_execution_latency: float
    sla_target: float
