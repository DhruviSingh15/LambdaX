import numpy as np
import warnings
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error

warnings.filterwarnings("ignore")

class ARIMAPredictor:
    def __init__(self, order=(1, 0, 0)):
        self.order = order
        self.model_res = None
        
    def fit(self, train_series):
        model = ARIMA(train_series, order=self.order)
        self.model_res = model.fit()
        return self
        
    def predict_rolling(self, test_series):
        """
        Efficiently generates 1-step ahead predictions for the test_series
        without re-estimating the ARIMA parameters.
        """
        if self.model_res is None:
            raise ValueError("Model is not fitted")
            
        # Apply the fitted parameters to the new data
        res_test = self.model_res.apply(test_series)
        
        # fittedvalues provides the 1-step ahead in-sample predictions for the applied data
        return res_test.fittedvalues if isinstance(res_test.fittedvalues, np.ndarray) else res_test.fittedvalues.values
        
    def predict_multi_step(self, history_series, steps=1):
        """
        Forecast `steps` into the future from the end of history_series.
        """
        model = ARIMA(history_series, order=self.order)
        # We can just apply parameters rather than re-fitting
        res = model.filter(self.model_res.params)
        forecast = res.forecast(steps=steps)
        return forecast if isinstance(forecast, np.ndarray) else forecast.values

def select_best_arima_order(train_series, val_series, orders=[(1,0,0), (1,1,0), (1,1,1), (2,1,1), (2,1,2)]):
    best_order = None
    best_rmse = float('inf')
    
    for order in orders:
        try:
            print(f"Testing ARIMA{order}...")
            predictor = ARIMAPredictor(order=order)
            predictor.fit(train_series)
            
            preds = predictor.predict_rolling(val_series)
            rmse = np.sqrt(mean_squared_error(val_series, preds))
            print(f"  RMSE: {rmse:.4f}")
            
            if rmse < best_rmse:
                best_rmse = rmse
                best_order = order
        except Exception as e:
            print(f"  Failed: {e}")
            
    print(f"Selected best order: {best_order} with RMSE: {best_rmse:.4f}")
    return best_order
