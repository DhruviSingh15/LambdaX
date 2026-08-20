import math

class CapacityEstimator:
    """
    Translates a predicted demand (RPS) into a concrete number of required containers.
    """
    def __init__(self, expected_execution_time_sec: float = 0.1, concurrency_per_container: int = 1):
        self.expected_execution_time_sec = expected_execution_time_sec
        self.concurrency_per_container = concurrency_per_container

    def estimate_capacity(self, predicted_rps: float) -> int:
        """
        Calculates the required number of containers to handle the predicted RPS.
        Formula: C = ceil((lambda * E[T]) / K)
        
        Args:
            predicted_rps (float): The forecasted number of requests per second.
            
        Returns:
            int: The desired number of active containers.
        """
        if predicted_rps <= 0:
            return 0
            
        required = (predicted_rps * self.expected_execution_time_sec) / self.concurrency_per_container
        return math.ceil(required)

    def update_expected_execution_time(self, new_avg_sec: float):
        """
        Dynamically update the expected execution time based on live telemetry (useful for Phase 6/7).
        """
        self.expected_execution_time_sec = new_avg_sec
