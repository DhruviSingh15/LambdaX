import pandas as pd
import numpy as np
import argparse
import time
import json
import os

from backend.prediction.naive import NaivePredictor
from backend.prediction.moving_average import MovingAveragePredictor
from backend.prediction.exponential_smoothing import ExponentialSmoothingPredictor

def evaluate_model(model, df, val_col='invocations', horizon=1, k_sigma=3.0, history_window=30):
    y_true = df[val_col].values
    n = len(y_true)
    
    if n == 0:
        return None
        
    y_pred = np.zeros(n)
    latencies = []
    
    # We will simulate streaming data
    history = []
    
    for i in range(n):
        # Predict the current step based on history up to i-1
        start_time = time.perf_counter()
        pred = model.predict(history, horizon)
        latency = (time.perf_counter() - start_time) * 1000 # ms
        
        y_pred[i] = pred
        latencies.append(latency)
        
        # Now observe the actual value and update history
        actual = y_true[i]
        history.append(actual)
        if len(history) > history_window:
            history.pop(0)
            
    # Calculate metrics
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    
    # Burst metrics
    mean = np.mean(y_true)
    std = np.std(y_true)
    threshold = mean + k_sigma * std
    
    actual_bursts = (y_true > threshold).astype(int)
    predicted_bursts = (y_pred > threshold).astype(int)
    
    true_positives = np.sum((actual_bursts == 1) & (predicted_bursts == 1))
    false_positives = np.sum((actual_bursts == 0) & (predicted_bursts == 1))
    false_negatives = np.sum((actual_bursts == 1) & (predicted_bursts == 0))
    
    recall = true_positives / np.sum(actual_bursts) if np.sum(actual_bursts) > 0 else 1.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
    
    return {
        "model": model.name,
        "mae": float(mae),
        "rmse": float(rmse),
        "burst_recall": float(recall),
        "burst_precision": float(precision),
        "avg_forecast_latency_ms": float(np.mean(latencies))
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Predictors Offline")
    parser.add_argument("test_csv", help="Input test CSV file")
    parser.add_argument("--val-col", default="invocations", help="Column to predict")
    parser.add_argument("--out", help="Output CSV file path")
    args = parser.parse_args()
    
    if not os.path.exists(args.test_csv):
        print(f"File {args.test_csv} not found.")
        return
        
    df = pd.read_csv(args.test_csv)
    
    models = [
        NaivePredictor(),
        MovingAveragePredictor(window=5),
        MovingAveragePredictor(window=10),
        ExponentialSmoothingPredictor(alpha=0.3),
        ExponentialSmoothingPredictor(alpha=0.7)
    ]
    
    results = []
    for model in models:
        metrics = evaluate_model(model, df, val_col=args.val_col)
        if metrics:
            metrics['dataset'] = os.path.basename(args.test_csv)
            results.append(metrics)
            
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        pd.DataFrame(results).to_csv(args.out, index=False)
        print(f"Saved results to {args.out}")
    else:
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
