from backend.prediction.ml.dataset import load_phase5_dataset
from backend.prediction.ml.arima_predictor import select_best_arima_order

def test_arima():
    train_df, val_df, test_df = load_phase5_dataset("hello")
    print(f"Train: {len(train_df)}, Val: {len(val_df)}")
    
    # We only need the invocations column
    train_series = train_df['invocations'].values
    val_series = val_df['invocations'].values
    
    select_best_arima_order(train_series, val_series)
    
if __name__ == "__main__":
    test_arima()
