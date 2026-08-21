import os
import json
import time
import numpy as np
import pandas as pd

from backend.prediction.ml.dataset import load_phase5_dataset
from backend.prediction.ml.features import build_features
from backend.prediction.ml.arima_predictor import ARIMAPredictor, select_best_arima_order
from backend.prediction.ml.xgboost_predictor import XGBoostPredictor
from backend.prediction.ml.hybrid_predictor import HybridPredictor
from backend.prediction.ml.metrics import calculate_metrics
from backend.prediction.ml.diagnostics import print_diagnostics

from backend.prediction.naive import NaivePredictor
from backend.prediction.moving_average import MovingAveragePredictor
from backend.prediction.exponential_smoothing import ExponentialSmoothingPredictor

def evaluate_model_streaming(model_name, model_obj, df, target_col='invocations', horizon=1, frozen_threshold=None):
    y_true = df[target_col].values
    n = len(y_true)
    
    if n == 0:
        return None
        
    y_pred = np.zeros(n)
    latencies = []
    
    history = []
    
    for i in range(n):
        # Time T is i. We only have data up to i-1
        start_time = time.perf_counter()
        
        # Predict 
        if hasattr(model_obj, "predict_multi_step"):
            # ARIMAPredictor
            try:
                pred = model_obj.predict_multi_step(history, steps=horizon)[-1]
            except:
                pred = np.mean(history) if len(history) > 0 else 0
        elif hasattr(model_obj, "predict") and "Predictor" in str(type(model_obj)):
            if type(model_obj) in [NaivePredictor, MovingAveragePredictor, ExponentialSmoothingPredictor]:
                pred = model_obj.predict(history, horizon)
            else:
                # XGBoost / Hybrid expect DataFrames
                # Since we are doing streaming, we should pass the single row
                test_row = df.iloc[[i]]
                if isinstance(model_obj, HybridPredictor):
                    pred = model_obj.predict(history, horizon=horizon, test_df=test_row)
                else:
                    # XGBoost
                    pred = model_obj.predict(test_row)[-1]
        else:
            pred = 0
            
        latency = (time.perf_counter() - start_time) * 1000 # ms
        
        y_pred[i] = pred
        latencies.append(latency)
        
        # Observe actual
        history.append(y_true[i])
        
    # Calculate metrics by aligning predictions with their actual future targets
    valid_n = n - horizon + 1
    if valid_n <= 0:
        return None, y_pred
        
    y_pred = np.nan_to_num(y_pred, nan=0.0)
        
    # y_pred[i] predicts y_true[i + horizon - 1]
    y_pred_aligned = y_pred[:valid_n]
    y_true_aligned = y_true[(horizon - 1):]
    latencies_aligned = latencies[:valid_n]
    
    metrics = calculate_metrics(y_true_aligned, y_pred_aligned, latencies=latencies_aligned, frozen_threshold=frozen_threshold)
    metrics['model'] = model_name
    metrics['horizon'] = horizon
    return metrics, y_pred

def main():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../experiments/configs/phase6/phase6_master.json"))
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    print("Loading Phase 5 datasets...")
    train_df, val_df, test_df = load_phase5_dataset("hello")
    
    print("Building Leakage-Safe Features...")
    train_feats = build_features(train_df)
    val_feats = build_features(val_df)
    test_feats = build_features(test_df)
    
    # We need to make sure they have the same columns
    # We can just align them or fillna
    common_cols = list(set(train_feats.columns) & set(val_feats.columns) & set(test_feats.columns))
    train_feats = train_feats[common_cols]
    val_feats = val_feats[common_cols]
    test_feats = test_feats[common_cols]
    
    print("Selecting Best ARIMA order...")
    best_order = select_best_arima_order(train_feats['invocations'].values, val_feats['invocations'].values, config['arima_orders'])
    if best_order is None:
        best_order = (1, 0, 0)
        
    print("Training Models...")
    arima = ARIMAPredictor(order=best_order)
    arima.fit(train_feats['invocations'].values)
    
    xgb = XGBoostPredictor(**config['xgboost'])
    xgb.fit(train_feats)
    
    hybrid = HybridPredictor(arima_order=best_order, xgb_params=config['xgboost'])
    hybrid.fit(train_feats)
    
    models = {
        "Naive": NaivePredictor(),
        "MA": MovingAveragePredictor(window=10),
        "EMA": ExponentialSmoothingPredictor(alpha=0.3),
        "ARIMA": arima,
        "XGBoost": xgb,
        "Hybrid": hybrid
    }
    
    horizons = config['horizons']
    results = []
    
    # Freeze burst threshold from training data
    train_y = train_feats['invocations'].values
    train_mean = np.mean(train_y)
    train_std = np.std(train_y)
    frozen_threshold = train_mean + 3.0 * train_std
    
    # Also evaluate on horizon=1 to get diagnostics
    print("Running Horizon=1 for Diagnostics...")
    _, arima_preds = evaluate_model_streaming("ARIMA", arima, test_feats, horizon=1, frozen_threshold=frozen_threshold)
    print_diagnostics(test_feats['invocations'].values, arima_preds, "ARIMA")
    
    _, hybrid_preds = evaluate_model_streaming("Hybrid", hybrid, test_feats, horizon=1, frozen_threshold=frozen_threshold)
    print_diagnostics(test_feats['invocations'].values, hybrid_preds, "Hybrid")
    
    print("Evaluating over all Horizons...")
    for h in horizons:
        for m_name, m_obj in models.items():
            print(f"Evaluating {m_name} (h={h})...")
            metrics, _ = evaluate_model_streaming(m_name, m_obj, test_feats, horizon=h, frozen_threshold=frozen_threshold)
            if metrics:
                results.append(metrics)
                
    # Calculate EMA improvement
    df_res = pd.DataFrame(results)
    
    for h in horizons:
        ema_row = df_res[(df_res['model'] == 'EMA') & (df_res['horizon'] == h)]
        hyb_row = df_res[(df_res['model'] == 'Hybrid') & (df_res['horizon'] == h)]
        
        if not ema_row.empty and not hyb_row.empty:
            ema_rmse = ema_row.iloc[0]['RMSE']
            hyb_rmse = hyb_row.iloc[0]['RMSE']
            if ema_rmse > 0:
                imp = ((ema_rmse - hyb_rmse) / ema_rmse) * 100
                print(f"Horizon {h}s -> Hybrid Improvement over EMA (RMSE): {imp:.2f}%")
                
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../experiments/results/phase6"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "phase6_offline_evaluation.csv")
    df_res.to_csv(out_path, index=False)
    print(f"Saved results to {out_path}")

if __name__ == "__main__":
    main()
