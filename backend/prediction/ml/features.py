import pandas as pd
import numpy as np

def build_features(df: pd.DataFrame, lags=[1, 2, 5], rolling_windows=[5], target_col='invocations') -> pd.DataFrame:
    """
    Builds leakage-safe features for XGBoost.
    For each row (time t), the features are computed strictly using data from time t-1 and earlier.
    The target for the row will be `target_col` at time t.
    """
    out = df.copy()
    
    # Sort just in case, but we expect it to be chronological
    if 'timestamp' in out.columns:
        out = out.sort_values('timestamp')
        
    # Create the base shifted column (which represents demand at t-1)
    # This guarantees we never leak demand(t) into the features for row t.
    shifted = out[target_col].shift(1)
    
    # 1. Lag features
    for lag in lags:
        # lag=1 means demand at t-1 (which is shifted by 1)
        # lag=2 means demand at t-2 (which is shifted by 2)
        out[f'lag_{lag}'] = out[target_col].shift(lag)
        
    # 2. Rolling features
    for w in rolling_windows:
        # We must roll over the `shifted` array, NOT the original target array!
        # If we roll over shifted, rolling mean at time t is mean(demand(t-w) ... demand(t-1))
        out[f'rolling_mean_{w}'] = shifted.rolling(window=w).mean()
        out[f'rolling_std_{w}'] = shifted.rolling(window=w).std()
        
    # 3. Burst indicators
    # Burst if t-1 was > mean + 2*std
    if 'rolling_mean_5' in out.columns and 'rolling_std_5' in out.columns:
        # Avoid division by zero
        std_safe = out['rolling_std_5'].replace(0, 1e-9)
        out['demand_zscore'] = (shifted - out['rolling_mean_5']) / std_safe
        out['burst_indicator'] = (out['demand_zscore'] > 2.0).astype(int)
        out['demand_above_rolling_mean'] = (shifted > out['rolling_mean_5']).astype(int)
        
    # 4. Temporal features
    if 'timestamp' in out.columns:
        dt = pd.to_datetime(out['timestamp'])
        out['hour'] = dt.dt.hour
        out['minute'] = dt.dt.minute
        out['day_of_week'] = dt.dt.dayofweek
        out['day_of_month'] = dt.dt.day
        
    # Drop rows with NaNs caused by shifting
    out = out.dropna().reset_index(drop=True)
    
    return out
