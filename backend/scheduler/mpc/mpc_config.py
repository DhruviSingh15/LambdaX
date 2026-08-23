from dataclasses import dataclass
import json
import os

@dataclass
class MPCConfig:
    horizon: int = 4
    step_seconds: int = 5
    cost_weight: float = 1.0
    latency_weight: float = 1.0
    sla_weight: float = 2.0
    queue_weight: float = 1.0
    max_start_rate: int = 5
    max_prewarm_per_step: int = 3
    
    @classmethod
    def load_from_file(cls, filepath="mpc_config.json"):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                print(f"[MPCConfig] Failed to load {filepath}: {e}")
        return cls()
