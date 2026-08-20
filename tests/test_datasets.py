import pandas as pd
import os

def test_dataset(base_name, dir_path):
    train_file = os.path.join(dir_path, f"{base_name}_train.csv")
    val_file = os.path.join(dir_path, f"{base_name}_val.csv")
    test_file = os.path.join(dir_path, f"{base_name}_test.csv")
    
    if not all(os.path.exists(f) for f in [train_file, val_file, test_file]):
        print(f"Skipping {base_name}: missing splits.")
        return
        
    df_train = pd.read_csv(train_file)
    df_val = pd.read_csv(val_file)
    df_test = pd.read_csv(test_file)
    
    # 1. No missing buckets (must be continuous)
    # The timestamps should be sorted and equidistant if normalized properly.
    # Wait, the feature script doesn't guarantee equidistance if not resampled.
    # But let's check temporal ordering.
    
    # Ensure they are sorted
    for df, name in [(df_train, "Train"), (df_val, "Val"), (df_test, "Test")]:
        if 'timestamp' in df.columns:
            is_sorted = df['timestamp'].is_monotonic_increasing
            print(f"[{base_name}] {name} is sorted: {is_sorted}")
            if not is_sorted:
                print(f"  FAIL: {name} is not strictly sorted chronologically.")
                
            # Duplicate check
            dups = df['timestamp'].duplicated().sum()
            print(f"[{base_name}] {name} duplicate timestamps: {dups}")
            if dups > 0:
                print(f"  FAIL: {name} has duplicate timestamps.")
    
    # 2. Check leakage (no future samples in training)
    # Max timestamp in train must be < Min timestamp in val
    # Max timestamp in val must be < Min timestamp in test
    train_max = df_train['timestamp'].max()
    val_min = df_val['timestamp'].min()
    val_max = df_val['timestamp'].max()
    test_min = df_test['timestamp'].min()
    
    leakage1 = train_max >= val_min
    leakage2 = val_max >= test_min
    
    print(f"[{base_name}] Leakage check Train->Val (Train max < Val min): {not leakage1}")
    print(f"[{base_name}] Leakage check Val->Test (Val max < Test min): {not leakage2}")
    
    if leakage1 or leakage2:
        print(f"  FAIL: Temporal leakage detected!")
    
    print("-" * 40)

if __name__ == "__main__":
    test_dataset("hello_1s_features", "datasets/processed/lambdax_timeseries")
