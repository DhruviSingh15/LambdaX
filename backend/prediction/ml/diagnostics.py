import numpy as np
import pandas as pd

def arima_diagnostics(actual, predicted):
    """
    Computes diagnostics on ARIMA residuals to determine if there is predictable structure remaining.
    """
    residuals = actual - predicted
    
    res_mean = np.mean(residuals)
    res_std = np.std(residuals)
    
    # Calculate lag-1 autocorrelation of residuals
    if len(residuals) > 1 and res_std > 0:
        res_series = pd.Series(residuals)
        res_autocorr = res_series.autocorr(lag=1)
    else:
        res_autocorr = 0.0
        
    return {
        "residual_mean": float(res_mean),
        "residual_std": float(res_std),
        "residual_autocorr_lag1": float(res_autocorr)
    }

def print_diagnostics(actual, predicted, label="ARIMA"):
    diag = arima_diagnostics(actual, predicted)
    print(f"--- {label} Diagnostics ---")
    print(f"Residual Mean: {diag['residual_mean']:.4f}")
    print(f"Residual Std:  {diag['residual_std']:.4f}")
    print(f"Autocorr (Lag 1): {diag['residual_autocorr_lag1']:.4f}")
    print("-------------------------")
    return diag
