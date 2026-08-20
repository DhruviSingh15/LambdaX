import pandas as pd
import argparse

def normalize_timeseries(filepath, freq='1s', time_col='timestamp', val_col='invocations'):
    """
    Normalizes a timeseries to have a continuous, unbroken index at the specified frequency.
    Missing intervals will be filled with 0.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
        
    if time_col not in df.columns or val_col not in df.columns:
        print(f"Missing required columns in {filepath}. Expected {time_col} and {val_col}.")
        return None
        
    df[time_col] = pd.to_datetime(df[time_col])
    
    # Sort and set index
    df = df.sort_values(time_col)
    df = df.set_index(time_col)
    
    # Resample to make the series continuous, filling missing with 0
    # If there are duplicates in the time_col, we should sum them first
    resampled = df[val_col].resample(freq).sum().fillna(0).reset_index()
    
    return resampled

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize Time Series")
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("output_csv", help="Output CSV file")
    parser.add_argument("--freq", default="1s", help="Resampling frequency (e.g. 1s, 1min)")
    args = parser.parse_args()
    
    normalized = normalize_timeseries(args.input_csv, args.freq)
    if normalized is not None:
        normalized.to_csv(args.output_csv, index=False)
        print(f"Normalized series saved to {args.output_csv}")
