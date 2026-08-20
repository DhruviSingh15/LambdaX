import json
import os
from enum import Enum

class SLAStatus(Enum):
    LARGE_POSITIVE = "LARGE_POSITIVE"
    SMALL_POSITIVE = "SMALL_POSITIVE"
    CRITICAL = "CRITICAL"
    VIOLATED = "VIOLATED"

class SLAEngine:
    def __init__(self, config_path: str = "backend/scheduler/adaptive/config.json"):
        self.thresholds = self._load_thresholds(config_path)

    def _load_thresholds(self, config_path: str) -> dict:
        default_thresholds = {
            "large_positive_ms": 500,
            "small_positive_ms": 100,
            "critical_ms": 0
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("sla_thresholds", default_thresholds)
            except Exception:
                pass
        return default_thresholds

    def evaluate(self, sla_ms: float, estimated_latency_ms: float) -> tuple[float, SLAStatus]:
        margin = sla_ms - estimated_latency_ms
        
        if margin >= self.thresholds.get("large_positive_ms", 500):
            status = SLAStatus.LARGE_POSITIVE
        elif margin >= self.thresholds.get("small_positive_ms", 100):
            status = SLAStatus.SMALL_POSITIVE
        elif margin >= self.thresholds.get("critical_ms", 0):
            status = SLAStatus.CRITICAL
        else:
            status = SLAStatus.VIOLATED
            
        return margin, status
