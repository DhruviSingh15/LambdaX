from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import uuid

class FunctionConfig(BaseModel):
    name: str
    image: str
    memory_mb: int = 128
    sla_ms: int = 1000

class FunctionRecord(FunctionConfig):
    function_id: str
    created_at: datetime

class FunctionRegistry:
    def __init__(self):
        self.functions: Dict[str, FunctionRecord] = {}

    def register(self, config: FunctionConfig) -> FunctionRecord:
        func_id = str(uuid.uuid4())
        record = FunctionRecord(
            function_id=func_id,
            name=config.name,
            image=config.image,
            memory_mb=config.memory_mb,
            sla_ms=config.sla_ms,
            created_at=datetime.utcnow()
        )
        self.functions[config.name] = record
        return record

    def get(self, name: str) -> Optional[FunctionRecord]:
        return self.functions.get(name)

    def list_all(self) -> List[FunctionRecord]:
        return list(self.functions.values())

registry = FunctionRegistry()
