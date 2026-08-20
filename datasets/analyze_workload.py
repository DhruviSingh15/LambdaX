import pandas as pd
import numpy as np
import argparse
import os
import json

def analyze_timeseries(filepath, val_col='invocations', k_sigma=3.0):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return None
        
    df = pd.read_csv(filepath)
    if val_col not in df.columns:
        print(f"Column {val_col} not found in {filepath}")
        return None
        
    y = df[val_col].values
    n = len(y)
    if n == 0:
        return None
        
    # Basic statistics
    mean = np.mean(y)
    median = np.median(y)
    std = np.std(y)
    var = np.var(y)
    min_val = np.min(y)
    max_val = np.max(y)
    
    # Traffic statistics
    peak_to_avg = max_val / mean if mean > 0 else 0
    cov = std / mean if mean > 0 else 0
    
    # Burst detection
    # A burst is when RPS > mean + k * std
    threshold = mean + k_sigma * std
    burst_mask = y > threshold
    
    burst_count = np.sum(burst_mask)
    burst_frequency = burst_count / n if n > 0 else 0
    
    # Find contiguous burst periods
    # Diff of the boolean mask gives 1 at start of burst, -1 at end
    diffs = np.diff(burst_mask.astype(int), prepend=0, append=0)
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    
    burst_durations = ends - starts
    avg_burst_duration = np.mean(burst_durations) if len(burst_durations) > 0 else 0
    
    burst_magnitudes = [np.mean(y[s:e]) for s, e in zip(starts, ends)] if len(starts) > 0 else []
    avg_burst_magnitude = np.mean(burst_magnitudes) if burst_magnitudes else 0
    
    inter_burst_intervals = starts[1:] - ends[:-1] if len(starts) > 1 else []
    avg_inter_burst = np.mean(inter_burst_intervals) if len(inter_burst_intervals) > 0 else 0
    
    # Temporal characteristics (Autocorrelation)
    # Simple lag-1 autocorrelation
    y_mean = y - mean
    if var > 0:
        autocorr_1 = np.sum(y_mean[:-1] * y_mean[1:]) / (np.sum(y_mean**2))
    else:
        autocorr_1 = 0
        
    results = {
        "basic": {
            "mean": float(mean),
            "median": float(median),
            "std": float(std),
            "variance": float(var),
            "min": float(min_val),
            "max": float(max_val)
        },
        "traffic": {
            "peak_to_avg_ratio": float(peak_to_avg),
            "coefficient_of_variation": float(cov)
        },
        "burst": {
            "threshold": float(threshold),
            "burst_frequency": float(burst_frequency),
            "total_burst_periods": int(len(starts)),
            "avg_burst_duration": float(avg_burst_duration),
            "avg_burst_magnitude": float(avg_burst_magnitude),
            "avg_inter_burst_interval": float(avg_inter_burst)
        },
        "temporal": {
            "autocorrelation_lag_1": float(autocorr_1)
        }
    }
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Workload Timeseries")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("--val-col", default="invocations", help="Column to analyze")
    parser.add_argument("--k-sigma", type=float, default=3.0, help="Burst threshold multiplier")
    args = parser.parse_args()
    
    results = analyze_timeseries(args.input_csv, args.val_col, args.k_sigma)
    if results:
        print(json.dumps(results, indent=2))
