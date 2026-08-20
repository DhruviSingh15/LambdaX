import pandas as pd
import argparse
import os

def split_timeseries(filepath, train_ratio=0.6, val_ratio=0.2):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return
        
    df = pd.read_csv(filepath)
    n = len(df)
    
    if n == 0:
        print("Empty dataframe.")
        return
        
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    base_name = os.path.splitext(filepath)[0]
    
    train_file = f"{base_name}_train.csv"
    val_file = f"{base_name}_val.csv"
    test_file = f"{base_name}_test.csv"
    
    train_df.to_csv(train_file, index=False)
    val_df.to_csv(val_file, index=False)
    test_df.to_csv(test_file, index=False)
    
    print(f"Split {n} rows into:")
    print(f"  Train: {len(train_df)} rows ({train_file})")
    print(f"  Val:   {len(val_df)} rows ({val_file})")
    print(f"  Test:  {len(test_df)} rows ({test_file})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chronological Train/Val/Test Split")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("--train", type=float, default=0.6, help="Train ratio")
    parser.add_argument("--val", type=float, default=0.2, help="Validation ratio")
    args = parser.parse_args()
    
    split_timeseries(args.input_csv, args.train, args.val)
