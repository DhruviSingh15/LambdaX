import pandas as pd
import os
import glob

def load_phase5_dataset(function_name="hello", resolution="1s"):
    """
    Loads the exact frozen chronological splits from Phase 5.
    Returns: (train_df, val_df, test_df)
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../datasets/processed/lambdax_timeseries"))
    
    prefix = f"{function_name}_{resolution}_features"
    train_path = os.path.join(base_dir, f"{prefix}_train.csv")
    val_path = os.path.join(base_dir, f"{prefix}_val.csv")
    test_path = os.path.join(base_dir, f"{prefix}_test.csv")
    
    if not os.path.exists(train_path) or not os.path.exists(val_path) or not os.path.exists(test_path):
        raise FileNotFoundError(f"Missing Phase 5 datasets at {base_dir}")
        
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)
    
    # Ensure chronological sort
    train_df = train_df.sort_values('timestamp').reset_index(drop=True)
    val_df = val_df.sort_values('timestamp').reset_index(drop=True)
    test_df = test_df.sort_values('timestamp').reset_index(drop=True)
    
    return train_df, val_df, test_df
