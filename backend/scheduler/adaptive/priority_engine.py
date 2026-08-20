import json
import os
from backend.database import db

class PriorityEngine:
    def __init__(self, config_path: str = "backend/scheduler/adaptive/config.json"):
        self.weights = self._load_weights(config_path)

    def _load_weights(self, config_path: str) -> dict:
        default_weights = {
            "cold_start": 0.25,
            "sla": 0.35,
            "queue": 0.20,
            "demand": 0.20
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("priority_weights", default_weights)
            except Exception:
                pass
        return default_weights

    def calculate_cold_start_penalty(self, function_id: int) -> float:
        # Fetch average cold start and warm start times for this function
        # from the telemetry/invocations table
        # We define cold start penalty as Avg(Cold Startup)
        # Actually user said: C_f = L_{cold,f} - L_{warm,f}
        
        # We need a robust query. For now, if we don't have enough data, return a default.
        query = """
            SELECT 
                AVG(CASE WHEN cold_start = 1 THEN execution_time_ms ELSE NULL END) as avg_cold,
                AVG(CASE WHEN cold_start = 0 THEN execution_time_ms ELSE NULL END) as avg_warm
            FROM invocations
            WHERE function_id = ?
        """
        res = db.execute_read_one(query, (function_id,))
        if res and res['avg_cold'] is not None and res['avg_warm'] is not None:
            penalty = res['avg_cold'] - res['avg_warm']
            return max(0.0, penalty)
            
        # fallback if not enough data
        return 500.0

    def calculate_priority(self, func: dict, queue_length: int, predicted_demand: float) -> float:
        w_c = self.weights.get("cold_start", 0.25)
        w_s = self.weights.get("sla", 0.35)
        w_q = self.weights.get("queue", 0.20)
        w_d = self.weights.get("demand", 0.20)

        # C_f: Normalize cold start penalty (e.g. assume max penalty around 2000ms)
        c_raw = self.calculate_cold_start_penalty(func['id'])
        c_f = min(c_raw / 2000.0, 1.0) 

        # S_f: SLA criticality
        sla_ms = func.get("sla_ms", 1000)
        s_f = min(1000.0 / sla_ms, 1.0) if sla_ms > 0 else 1.0

        # Q_f: Queue pressure (assume max acceptable queue ~10)
        q_f = min(queue_length / 10.0, 1.0)

        # D_f: Predicted demand (assume max RPS ~50 for normalization)
        d_f = min(predicted_demand / 50.0, 1.0)

        priority = (w_c * c_f) + (w_s * s_f) + (w_q * q_f) + (w_d * d_f)
        return priority
