import pandas as pd
import os
import argparse
from datetime import datetime, timedelta

# Default paths
RAW_DIR = "datasets/raw/azure_2019"
OUTPUT_DIR = "datasets/processed/azure_2019_timeseries"

def process_file(filepath, output_dir, day_offset=0):
    print(f"Processing {filepath}...")
    
    # Azure 2019 invocation files have columns: 
    # HashOwner, HashApp, HashFunction, Trigger, 1, 2, ..., 1440
    # where 1..1440 are the minutes in a day.
    
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Failed to read {filepath}: {e}")
        return
        
    # Check if this is the invocation count file
    if '1' not in df.columns or '1440' not in df.columns:
        print(f"File {filepath} doesn't look like the 2019 invocation trace. Skipping.")
        return

    # Identify metadata columns vs minute columns
    meta_cols = ['HashOwner', 'HashApp', 'HashFunction', 'Trigger']
    # Filter meta_cols to only those present in df
    meta_cols = [c for c in meta_cols if c in df.columns]
    
    minute_cols = [str(i) for i in range(1, 1441) if str(i) in df.columns]
    
    # Melt the dataframe (wide to long)
    print("  Melting dataframe to long format...")
    melted = pd.melt(df, id_vars=meta_cols, value_vars=minute_cols, 
                     var_name='minute_of_day', value_name='invocations')
    
    # Drop rows where invocations == 0 to save space, unless we want a continuous series
    # Actually, keeping 0 is good for continuous time series forecasting.
    
    # Convert 'minute_of_day' to an actual timestamp
    # Base date for day_offset (arbitrary start date for the dataset)
    base_date = datetime(2019, 7, 15) + timedelta(days=day_offset)
    
    print("  Computing timestamps...")
    # 'minute_of_day' goes from 1 to 1440. Subtract 1 to get 0 to 1439.
    melted['minute_of_day'] = melted['minute_of_day'].astype(int) - 1
    
    # Apply timedelta
    melted['timestamp'] = base_date + pd.to_timedelta(melted['minute_of_day'], unit='m')
    
    # Select final columns
    final_cols = ['timestamp'] + meta_cols + ['invocations']
    final_df = melted[final_cols]
    
    # Sort by timestamp
    print("  Sorting...")
    final_df = final_df.sort_values('timestamp')
    
    # Save to CSV
    filename = os.path.basename(filepath)
    out_file = os.path.join(output_dir, f"timeseries_{filename}")
    final_df.to_csv(out_file, index=False)
    print(f"  -> Saved {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Extract Azure 2019 Traces")
    parser.add_argument("--raw-dir", default=RAW_DIR, help="Path to raw 2019 files")
    parser.add_argument("--out-dir", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    if not os.path.exists(args.raw_dir):
        print(f"Raw directory {args.raw_dir} not found. Please place the Azure 2019 invocation files there.")
        return
        
    files = [f for f in os.listdir(args.raw_dir) if f.endswith('.csv')]
    if not files:
        print(f"No CSV files found in {args.raw_dir}.")
        
    for i, file in enumerate(sorted(files)):
        process_file(os.path.join(args.raw_dir, file), args.out_dir, day_offset=i)

if __name__ == "__main__":
    main()
