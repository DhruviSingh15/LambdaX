from backend.prediction.ml.arima_predictor import ARIMAPredictor
from backend.prediction.ml.xgboost_predictor import XGBoostPredictor

from backend.prediction.base_predictor import BasePredictor
from backend.prediction.ml.features import build_features
import numpy as np
import pandas as pd

class HybridPredictor(BasePredictor):
    def __init__(self, arima_order=(1,0,0), xgb_params=None, horizons=[5, 10, 30, 60]):
        super().__init__("hybrid")
        self.arima_order = arima_order
        self.xgb_params = xgb_params or {'n_estimators': 200, 'max_depth': 4, 'learning_rate': 0.05}
        self.horizons = horizons
        
        self.arima = ARIMAPredictor(order=self.arima_order)
        # Dictionary mapping horizon -> trained XGBoostPredictor
        self.xgbs = {}
        
    def fit(self, train_df, target_col='invocations'):
        """
        1. Fit ARIMA on the full training series.
        2. For each horizon:
            a. Generate horizon-specific out-of-sample ARIMA predictions.
            b. Calculate true future residual: r_{t,h} = y_{t+h} - y_hat_{t+h}
            c. Train a separate XGBoost model to predict r_{t,h} using features at t.
        """
        y_train = train_df[target_col].values
        n = len(y_train)
        
        min_fit_points = sum(self.arima_order) + 2
        
        # 1. Fit ARIMA
        self.arima.fit(y_train)
        
        # 2. Train horizon-specific XGBoost models
        for h in self.horizons:
            # We can only train if we have enough data to look h steps ahead
            if n <= min_fit_points + h:
                print(f"[HybridPredictor] Not enough data to train horizon {h}")
                continue
                
            xgb = XGBoostPredictor(**self.xgb_params)
            residuals = np.zeros(n)
            
            # Generate ARIMA predictions and compute residuals
            # We are at time i, predicting i+h
            for i in range(min_fit_points, n - h):
                history = y_train[:i+1] # history up to and including time i
                
                try:
                    # predict h steps ahead
                    arima_pred = self.arima.predict_multi_step(history, steps=h)[-1]
                except Exception:
                    arima_pred = np.mean(history)
                    
                actual_future = y_train[i + h]
                residuals[i] = actual_future - arima_pred
                
            # Create training df for XGBoost
            # features at t -> predict residual at t+h
            residual_df = train_df.copy()
            residual_df[target_col] = residuals
            
            # Since we only computed residuals up to n-h-1, we slice the dataframe
            # XGBoost should only learn from valid target rows
            valid_train = residual_df.iloc[min_fit_points : n - h]
            
            if not valid_train.empty:
                xgb.fit(valid_train, target_col=target_col)
                self.xgbs[h] = xgb
            
        return self
        
    def update(self, obs):
        pass
        
    def predict(self, history, horizon=1, test_df=None):
        """
        Predicts demand h steps ahead.
        Hybrid prediction = ARIMA forecast + XGBoost residual forecast
        Returns max(0, hybrid)
        """
        if len(history) == 0:
            return 0.0
            
        # 1. ARIMA forecast
        try:
            arima_pred = self.arima.predict_multi_step(history, steps=horizon)[-1]
        except Exception:
            arima_pred = np.mean(history)
            
        # 2. XGBoost residual prediction
        xgb_residual_pred = 0.0
        
        # We find the exact XGB model for this horizon, or fallback to nearest
        best_h = horizon
        if best_h not in self.xgbs:
            if self.xgbs:
                # Find closest horizon we trained on
                best_h = min(self.xgbs.keys(), key=lambda k: abs(k - horizon))
            else:
                best_h = None
                
        if best_h is not None:
            if test_df is None:
                # Build features from history
                df_hist = pd.DataFrame({'invocations': history})
                feats = build_features(df_hist, target_col='invocations')
                if len(feats) > 0:
                    test_row = feats.iloc[[-1]]
                else:
                    test_row = None
            else:
                test_row = test_df
                
            if test_row is not None:
                try:
                    xgb_residual_pred = self.xgbs[best_h].predict(test_row)[-1]
                except Exception:
                    xgb_residual_pred = 0.0
        
        # 3. Hybrid Forecast
        hybrid_pred = arima_pred + xgb_residual_pred
        
        # 4. Clip to 0
        return max(0.0, float(hybrid_pred))
