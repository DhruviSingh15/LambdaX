import sqlite3
import pandas as pd
import os
import argparse

DB_PATH = "lambdax.db"
OUTPUT_DIR = "datasets/processed/lambdax_timeseries"

def extract_lambdax(db_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        return

    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    
    # Read functions
    functions_df = pd.read_sql("SELECT id, name FROM functions", conn)
    function_map = dict(zip(functions_df['id'], functions_df['name']))
    
    # Read invocations
    query = """
    SELECT 
        function_id, 
        timestamp, 
        queue_time_ms, 
        cold_start, 
        execution_time_ms, 
        total_latency_ms,
        scheduling_policy
    FROM invocations
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print("No invocations found in database.")
        return
        
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Map function names
    df['function_name'] = df['function_id'].map(function_map)
    
    print(f"Loaded {len(df)} invocations.")
    
    buckets = ['1s', '5s', '10s', '30s', '60s']
    
    for bucket in buckets:
        print(f"Processing {bucket} buckets...")
        
        # We need to process each function and policy separately if needed,
        # but for timeseries extraction we mostly care about the raw demand per function.
        # Wait, demand is independent of policy! We just group by function and time bucket.
        
        # Group by function and bucket
        grouped = df.groupby(['function_name', pd.Grouper(key='timestamp', freq=bucket)])
        
        # Calculate metrics
        aggregated = grouped.agg(
            invocations=('function_id', 'count'),
            queue_time_mean=('queue_time_ms', 'mean'),
            execution_time_mean=('execution_time_ms', 'mean'),
            cold_start_rate=('cold_start', lambda x: x.mean())
        ).reset_index()
        
        # Save to CSV
        for func_name in aggregated['function_name'].unique():
            func_df = aggregated[aggregated['function_name'] == func_name].copy()
            # Sort by time
            func_df = func_df.sort_values('timestamp')
            
            out_file = os.path.join(output_dir, f"{func_name}_{bucket}.csv")
            func_df.to_csv(out_file, index=False)
            print(f"  -> Saved {out_file}")

if __name__ == "__main__":
    extract_lambdax(DB_PATH, OUTPUT_DIR)
