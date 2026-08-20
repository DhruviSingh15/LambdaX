from typing import List
from .base_predictor import BasePredictor

class ExponentialSmoothingPredictor(BasePredictor):
    """
    Exponential Moving Average (EMA) Predictor.
    EMA_t = alpha * Y_t + (1 - alpha) * EMA_{t-1}
    """
    
    def __init__(self, alpha: float = 0.5):
        super().__init__(name="ema")
        self.alpha = alpha
        self.current_ema = None

    def fit(self, data: List[float]):
        if not data:
            return
            
        # Initialize EMA with the first data point, then iterate
        self.current_ema = data[0]
        for y in data[1:]:
            self.current_ema = self.alpha * y + (1 - self.alpha) * self.current_ema

    def predict(self, history: List[float], horizon: int) -> float:
        # If history is provided, we can compute EMA on the fly to get the latest prediction
        # Otherwise, rely on the internal state
        if history and len(history) > 0:
            ema = history[0]
            for y in history[1:]:
                ema = self.alpha * y + (1 - self.alpha) * ema
            return float(ema)
            
        if self.current_ema is not None:
            return float(self.current_ema)
            
        return 0.0

    def update(self, observation: float):
        if self.current_ema is None:
            self.current_ema = observation
        else:
            self.current_ema = self.alpha * observation + (1 - self.alpha) * self.current_ema
