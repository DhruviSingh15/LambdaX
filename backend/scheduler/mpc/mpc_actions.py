from enum import Enum
from dataclasses import dataclass

class MPCActionType(Enum):
    MAINTAIN = "MAINTAIN"
    PREWARM = "PREWARM"
    RECLAIM = "RECLAIM"

@dataclass
class MPCAction:
    action_type: MPCActionType
    count: int = 0
    
    def __str__(self):
        if self.action_type == MPCActionType.MAINTAIN:
            return "MAINTAIN"
        elif self.action_type == MPCActionType.PREWARM:
            return f"PREWARM +{self.count}"
        elif self.action_type == MPCActionType.RECLAIM:
            return f"RECLAIM -{self.count}"
        return super().__str__()
