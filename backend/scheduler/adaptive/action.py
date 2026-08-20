from enum import Enum
from dataclasses import dataclass
from typing import Optional

class DecisionAction(Enum):
    PREWARM = "PREWARM"
    SCALE_UP = "SCALE_UP"
    MAINTAIN_WARM = "MAINTAIN_WARM"
    MICRO_QUEUE = "MICRO_QUEUE"
    RECLAIM = "RECLAIM"
    SCALE_DOWN = "SCALE_DOWN"
    EMERGENCY_REACTIVE = "EMERGENCY_REACTIVE"


