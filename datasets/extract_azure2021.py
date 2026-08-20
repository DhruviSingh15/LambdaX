import pandas as pd
import os
import argparse

# Default paths
RAW_DIR = "datasets/raw/azure_2021"
OUTPUT_DIR = "datasets/processed/azure_2021_timeseries"

def process_file(filepath, output_dir):
    print(f"Processing {filepath}...")
    
    # Azure 2021 invocation files typically have:
    # app, func, end_timestamp, duration
    
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Failed to read {filepath}: {e}")
        return
        
    expected_cols = ['app', 'func', 'end_timestamp', 'duration']
    if not all(c in df.columns for c in expected_cols):
        print(f"File {filepath} is missing expected columns. Skipping.")
        return

    # Convert end_timestamp to datetime
    # We assume end_timestamp is in seconds (or fractional seconds) since epoch or start of trace.
    # We will convert it to a timedelta and add to a base date.
    
    print("  Computing timestamps...")
    # If end_timestamp is numeric (seconds), convert to timedelta
    if pd.api.types.is_numeric_dtype(df['end_timestamp']):
        base_date = pd.Timestamp("2021-01-31")
        df['timestamp'] = base_date + pd.to_timedelta(df['end_timestamp'], unit='s')
    else:
        df['timestamp'] = pd.to_datetime(df['end_timestamp'])
        
    print("  Sorting...")
    df = df.sort_values('timestamp')
    
    buckets = ['1s', '5s', '10s', '30s', '60s']
    
    for bucket in buckets:
        print(f"  Bucketing into {bucket}...")
        
        # Group by app, func, and time bucket
        grouped = df.groupby(['app', 'func', pd.Grouper(key='timestamp', freq=bucket)])
        
        aggregated = grouped.agg(
            invocations=('end_timestamp', 'count'),
            duration_mean=('duration', 'mean')
        ).reset_index()
        
        out_file = os.path.join(output_dir, f"{bucket}_{os.path.basename(filepath)}")
        aggregated.to_csv(out_file, index=False)
        print(f"    -> Saved {out_file}")

def main():
    parser = argparse.ArgumentParser(description="Extract Azure 2021 Traces")
    parser.add_argument("--raw-dir", default=RAW_DIR, help="Path to raw 2021 files")
    parser.add_argument("--out-dir", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    if not os.path.exists(args.raw_dir):
        print(f"Raw directory {args.raw_dir} not found. Please place the Azure 2021 files there.")
        return
        
    files = [f for f in os.listdir(args.raw_dir) if f.endswith('.csv')]
    if not files:
        print(f"No CSV files found in {args.raw_dir}.")
        
    for file in sorted(files):
        process_file(os.path.join(args.raw_dir, file), args.out_dir)

if __name__ == "__main__":
    main()
