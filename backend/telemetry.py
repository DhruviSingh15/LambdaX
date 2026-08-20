import json
from datetime import datetime
from typing import Dict, Any, List

class TelemetryLogger:
    def __init__(self, log_file: str = "telemetry_log.jsonl"):
        self.log_file = log_file

    def log_invocation(self, data: Dict[str, Any]):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
            
    def get_logs(self) -> List[Dict[str, Any]]:
        logs = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    logs.append(json.loads(line))
        except FileNotFoundError:
            pass
        return logs

telemetry_logger = TelemetryLogger()
