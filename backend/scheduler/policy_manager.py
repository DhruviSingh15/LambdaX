from backend.scheduler.reactive import ReactivePolicy
from backend.scheduler.fixed_pool import FixedPoolPolicy
from backend.scheduler.threshold import ThresholdPolicy
from backend.scheduler.predictive import PredictivePolicy
from backend.prediction.base_predictor import BasePredictor
from backend.prediction.exponential_smoothing import ExponentialSmoothingPredictor
from backend.prediction.moving_average import MovingAveragePredictor
from backend.prediction.naive import NaivePredictor
from backend.prediction.ml.hybrid_predictor import HybridPredictor
from backend.prediction.ml.dataset import load_phase5_dataset
from backend.prediction.ml.features import build_features

class CrashingPredictor(BasePredictor):
    def __init__(self): super().__init__("crashing")
    def fit(self, data): pass
    def predict(self, history, horizon): raise Exception("Simulated Predictor Crash")
    def update(self, obs): pass

class InvalidPredictor(BasePredictor):
    def __init__(self): super().__init__("invalid")
    def fit(self, data): pass
    def predict(self, history, horizon): return -100  # invalid demand
    def update(self, obs): pass

class ZeroPredictor(BasePredictor):
    def __init__(self): super().__init__("zero")
    def fit(self, data): pass
    def predict(self, history, horizon): return 0
    def update(self, obs): pass

def _create_trained_hybrid():
    try:
        train_df, _, _ = load_phase5_dataset("hello")
        train_feats = build_features(train_df)
        hybrid = HybridPredictor(arima_order=(1,0,0))
        hybrid.fit(train_feats)
        return hybrid
    except Exception as e:
        print(f"Failed to train Hybrid predictor on startup: {e}")
        return ExponentialSmoothingPredictor() # Fallback

from backend.scheduler.adaptive.adaptive_policy import AdaptivePolicy
from backend.scheduler.mpc.mpc_policy import MPCPolicy

class PolicyManager:
    def __init__(self):
        self.policies = {
            "reactive": ReactivePolicy(),
            "fixed": FixedPoolPolicy(),
            "threshold": ThresholdPolicy(),
            "predictive": PredictivePolicy(ExponentialSmoothingPredictor(alpha=0.5)),
            "predictive_naive": PredictivePolicy(NaivePredictor()),
            "predictive_ma": PredictivePolicy(MovingAveragePredictor(window=5)),
            "predictive_ema": PredictivePolicy(ExponentialSmoothingPredictor(alpha=0.5)),
            "predictive_hybrid": PredictivePolicy(_create_trained_hybrid()),
            "adaptive": AdaptivePolicy(_create_trained_hybrid()),
            "mpc": MPCPolicy(_create_trained_hybrid()),
            # Test Policies
            "test_crashing": PredictivePolicy(CrashingPredictor()),
            "test_invalid": PredictivePolicy(InvalidPredictor()),
            "test_zero": PredictivePolicy(ZeroPredictor())
        }
        self.last_forecasts = {}
        
    def get_policy(self, policy_name: str):
        return self.policies.get(policy_name, self.policies["reactive"])
        
    def set_last_forecast(self, func_id: str, history: list, forecast: list):
        self.last_forecasts[func_id] = {
            "history": history[-10:] if history else [],
            "forecast": forecast
        }
        
    def get_last_forecast(self, func_id: str = None):
        if not func_id:
            # return first available if none specified
            keys = list(self.last_forecasts.keys())
            if not keys: return {"history": [], "forecast": []}
            return self.last_forecasts[keys[0]]
        return self.last_forecasts.get(func_id, {"history": [], "forecast": []})

policy_manager = PolicyManager()
