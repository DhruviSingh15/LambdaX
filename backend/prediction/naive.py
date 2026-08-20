from typing import List
from .base_predictor import BasePredictor

class NaivePredictor(BasePredictor):
    """
    Naive Predictor (Baseline).
    Forecasts that the next value will be exactly the same as the last observed value.
    Y_{t+h} = Y_t
    """
    
    def __init__(self):
        super().__init__(name="naive")
        self.last_observation = 0.0

    def fit(self, data: List[float]):
        if data:
            self.last_observation = data[-1]

    def predict(self, history: List[float], horizon: int) -> float:
        # Naive prediction assumes constant demand, so horizon doesn't change the predicted value
        if history and len(history) > 0:
            return float(history[-1])
        return float(self.last_observation)

    def update(self, observation: float):
        self.last_observation = observation
