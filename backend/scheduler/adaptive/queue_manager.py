import time
from backend.database import db

class QueueManager:
    def __init__(self):
        pass

    def estimate_service_time(self, function_id: int) -> float:
        """
        Estimate the service time based on recent warm execution telemetry.
        """
        query = """
            SELECT AVG(execution_time_ms) as avg_exec
            FROM invocations
            WHERE function_id = ? AND cold_start = 0
        """
        res = db.execute_read_one(query, (function_id,))
        if res and res['avg_exec'] is not None:
            return max(res['avg_exec'], 10.0) # Assume at least 10ms
        
        # Default fallback
        return 100.0

    def calculate_expected_wait(self, function_id: int, queue_length: int) -> float:
        """
        Calculates the expected wait time for a newly arriving request.
        ExpectedWait = QueueLength * EstimatedServiceTime
        """
        if queue_length <= 0:
            return 0.0
            
        estimated_service_time = self.estimate_service_time(function_id)
        return float(queue_length) * estimated_service_time

    def analyze_queue(self, function_id: int, current_queue_length: int) -> dict:
        """
        Returns a summary of the queue state for the decision engine.
        """
        expected_wait = self.calculate_expected_wait(function_id, current_queue_length)
        service_time = self.estimate_service_time(function_id)
        
        return {
            "queue_length": current_queue_length,
            "expected_wait_ms": expected_wait,
            "estimated_service_time_ms": service_time
        }
