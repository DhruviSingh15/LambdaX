import time
import collections
from typing import Dict, Optional

from backend.prediction.base_predictor import BasePredictor
from backend.prediction.capacity_estimator import CapacityEstimator

class PredictorManager:
    """
    Manages the predictive pipeline for live functions:
    - Maintains the real-time Ring Buffer of incoming request timestamps.
    - Interfaces with the selected statistical Predictor.
    - Translates predicted RPS to Capacity requirements.
    """
    def __init__(self, predictor: BasePredictor, window_seconds: int = 60, horizon_seconds: int = 10):
        self.predictor = predictor
        self.capacity_estimator = CapacityEstimator(expected_execution_time_sec=0.1) # default 100ms
        self.window_seconds = window_seconds
        self.horizon_seconds = horizon_seconds
        
        # function_id -> deque of request timestamps
        self.request_buffers: Dict[str, collections.deque] = {}
        
    def record_request(self, function_id: str):
        """
        Record the arrival of a new request.
        """
        now = time.time()
        if function_id not in self.request_buffers:
            self.request_buffers[function_id] = collections.deque()
            
        self.request_buffers[function_id].append(now)
        
    def _get_recent_rps_history(self, function_id: str) -> list[float]:
        """
        Converts the raw timestamp ring buffer into a list of RPS values 
        over the last `window_seconds`.
        """
        if function_id not in self.request_buffers:
            return []
            
        now = time.time()
        cutoff = now - self.window_seconds
        
        buffer = self.request_buffers[function_id]
        
        # Evict old timestamps
        while buffer and buffer[0] < cutoff:
            buffer.popleft()
            
        # If no requests in window, return zeros
        if not buffer:
            return [0.0] * self.window_seconds
            
        # Bucket timestamps into 1-second intervals
        # For simplicity, we just count requests per second bin
        # We'll create an array of size `window_seconds` representing RPS
        rps_history = [0.0] * self.window_seconds
        for ts in buffer:
            # offset from cutoff in seconds (0 to window_seconds-1)
            offset = int(ts - cutoff)
            if 0 <= offset < self.window_seconds:
                rps_history[offset] += 1.0
                
        return rps_history

    def get_desired_capacity(self, function_id: str) -> int:
        """
        Runs the full predictive pipeline:
        1. Extract recent RPS history.
        2. Feed to predictor to get forecasted RPS.
        3. Feed to capacity estimator to get desired containers.
        """
        try:
            history = self._get_recent_rps_history(function_id)
            predicted_rps = self.predictor.predict(history, horizon=self.horizon_seconds)
            desired_capacity = self.capacity_estimator.estimate_capacity(predicted_rps)
            return desired_capacity
        except Exception as e:
            # Fallback to 0 if prediction fails (which lets Reactive take over)
            print(f"[PredictorManager] Error predicting capacity for {function_id}: {e}")
            return 0
