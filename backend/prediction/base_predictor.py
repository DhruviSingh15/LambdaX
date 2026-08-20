from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union
import time

class BasePredictor(ABC):
    """
    Abstract base class for all prediction algorithms in LambdaX.
    Predictors are strictly responsible for returning future RPS / invocation counts
    based on historical data. They do not interact with Docker or the PoolManager.
    """
    
    def __init__(self, name: str = "base"):
        self.name = name

    @abstractmethod
    def fit(self, data: List[float]):
        """
        Train or calibrate the model on historical data.
        For simple statistical models, this might just set the initial state.
        """
        pass

    @abstractmethod
    def predict(self, history: List[float], horizon: int) -> float:
        """
        Predict future demand based on recent history.
        
        Args:
            history: List of recent demand values (e.g., RPS over the last W intervals)
            horizon: The number of steps into the future to predict.
                     For simple models, predicting step t+1 might be extended to t+h by 
                     assuming constant demand or projecting a trend.
                     
        Returns:
            The predicted demand (float) for the target horizon.
        """
        pass

    @abstractmethod
    def update(self, observation: float):
        """
        Incrementally update the model's internal state with a new observation.
        """
        pass

    def create_forecast_result(self, function_id: str, horizon_seconds: int, predicted_rps: float, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Standardizes the output format of a prediction.
        """
        return {
            "model": self.name,
            "function_id": function_id,
            "timestamp": time.time(),
            "horizon_seconds": horizon_seconds,
            "predicted_rps": predicted_rps,
            "metadata": metadata or {}
        }
