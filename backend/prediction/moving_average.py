from typing import List
import numpy as np
from .base_predictor import BasePredictor

class MovingAveragePredictor(BasePredictor):
    """
    Moving Average Predictor.
    Forecasts the next value based on the average of the last `window` observations.
    """
    
    def __init__(self, window: int = 5):
        super().__init__(name="moving_average")
        self.window = window
        self.history_buffer = []

    def fit(self, data: List[float]):
        if data:
            self.history_buffer = list(data[-self.window:])

    def predict(self, history: List[float], horizon: int) -> float:
        # Prefer the provided history over internal state if available
        data_to_use = history if history and len(history) > 0 else self.history_buffer
        
        if not data_to_use:
            return 0.0
            
        recent = data_to_use[-self.window:]
        return float(np.mean(recent))

    def update(self, observation: float):
        self.history_buffer.append(observation)
        if len(self.history_buffer) > self.window:
            self.history_buffer.pop(0)
