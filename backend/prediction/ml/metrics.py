import numpy as np

def calculate_metrics(y_true, y_pred, k_sigma=3.0, latencies=None, frozen_threshold=None):
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    
    # Burst metrics
    if frozen_threshold is not None:
        threshold = frozen_threshold
    else:
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
    
    # Burst Lead Time
    # If there is a burst in actual at time T, when did the predictor first predict a burst?
    # We define it as the average lead time across all actual bursts.
    lead_times = []
    
    # Find indices where actual bursts start
    # A burst starts if actual[i] is a burst and actual[i-1] is not (or i=0)
    for i in range(len(actual_bursts)):
        if actual_bursts[i] == 1 and (i == 0 or actual_bursts[i-1] == 0):
            # Burst started at i
            # Look forwards from max(0, i-30) up to i to find the FIRST prediction
            lead = 0
            start_search = max(0, i-30)
            for j in range(start_search, i + 1):
                if predicted_bursts[j] == 1:
                    lead = i - j
                    break
            lead_times.append(lead)
            
    avg_lead_time = np.mean(lead_times) if lead_times else 0.0
    
    avg_lat = np.mean(latencies) if latencies else 0.0
    
    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "Burst_Precision": float(precision),
        "Burst_Recall": float(recall),
        "Burst_Lead_Time": float(avg_lead_time),
        "Forecast_Latency_ms": float(avg_lat)
    }
