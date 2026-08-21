import pandas as pd
import numpy as np
from scipy import stats
import sys
import os
import matplotlib.pyplot as plt

def analyze_results(csv_path, out_dir):
    os.makedirs(f"{out_dir}/figures", exist_ok=True)
    df = pd.read_csv(csv_path)
    
    # 1. Summary Statistics
    summary = df.groupby(['policy', 'workload']).agg(
        mean_p99=('p99_latency', 'mean'),
        std_p99=('p99_latency', 'std'),
        mean_sla=('sla_compliance', 'mean'),
        std_sla=('sla_compliance', 'std'),
        mean_cost=('container_seconds', 'mean'),
        std_cost=('container_seconds', 'std'),
        mean_cs=('cold_start_rate', 'mean')
    ).reset_index()
    summary.to_csv(f"{out_dir}/phase8_summary.csv", index=False)
    
    # 2. Paired T-Tests against Adaptive
    # We want paired tests (same workload, same seed)
    results = []
    baselines = ["reactive", "fixed", "threshold", "predictive_ema", "predictive_hybrid"]
    
    adaptive_df = df[df['policy'] == 'adaptive'].set_index(['workload', 'seed', 'function'])
    
    for base in baselines:
        base_df = df[df['policy'] == base].set_index(['workload', 'seed', 'function'])
        
        # Merge on index
        merged = adaptive_df.join(base_df, lsuffix='_adp', rsuffix='_base', how='inner')
        if len(merged) == 0:
            continue
            
        for metric in ['p99_latency', 'sla_compliance', 'container_seconds', 'cold_start_rate']:
            adp_vals = merged[f'{metric}_adp'].values
            base_vals = merged[f'{metric}_base'].values
            
            diff = adp_vals - base_vals
            mean_diff = np.mean(diff)
            median_diff = np.median(diff)
            
            # T-test
            t_stat, p_val = stats.ttest_rel(adp_vals, base_vals)
            
            # Wilcoxon signed-rank test
            try:
                w_stat, w_p_val = stats.wilcoxon(diff)
            except Exception:
                w_p_val = float('nan')
            
            # Effect size (Cohen's d)
            s_diff = np.std(diff, ddof=1)
            effect_size = mean_diff / s_diff if s_diff > 0 else 0
            
            # CI
            ci_low, ci_high = stats.t.interval(0.95, len(diff)-1, loc=mean_diff, scale=stats.sem(diff))
            
            results.append({
                'baseline': base,
                'metric': metric,
                'adp_mean': np.mean(adp_vals),
                'base_mean': np.mean(base_vals),
                'abs_diff': mean_diff,
                'rel_improvement_pct': (mean_diff / np.mean(base_vals) * 100) if np.mean(base_vals) > 0 else 0,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'effect_size': effect_size,
                'p_value_ttest': p_val,
                'p_value_wilcoxon': w_p_val,
                'n_pairs': len(diff)
            })
            
    pd.DataFrame(results).to_csv(f"{out_dir}/phase8_statistics.csv", index=False)
    
    # 3. Pareto Plots
    # Group by policy
    agg = df.groupby('policy').mean(numeric_only=True).reset_index()
    
    # Cost vs Latency
    plt.figure(figsize=(8,6))
    for i, row in agg.iterrows():
        plt.scatter(row['container_seconds'], row['p99_latency'], label=row['policy'], s=100)
        plt.text(row['container_seconds'], row['p99_latency'], row['policy'])
    plt.xlabel("Container Seconds (Lower is Better)")
    plt.ylabel("P99 Latency ms (Lower is Better)")
    plt.title("Pareto: Latency vs. Resource Cost")
    plt.grid(True)
    plt.savefig(f"{out_dir}/figures/pareto_latency_cost.png")
    
    # Cold Start vs SLA
    plt.figure(figsize=(8,6))
    for i, row in agg.iterrows():
        plt.scatter(row['cold_start_rate'], row['sla_compliance'], label=row['policy'], s=100)
        plt.text(row['cold_start_rate'], row['sla_compliance'], row['policy'])
    plt.xlabel("Cold Start Rate % (Lower is Better)")
    plt.ylabel("SLA Compliance % (Higher is Better)")
    plt.title("Pareto: SLA vs. Cold Starts")
    plt.grid(True)
    plt.savefig(f"{out_dir}/figures/pareto_coldstart_sla.png")

    print("Phase 8 Analysis Complete.")

if __name__ == "__main__":
    analyze_results(sys.argv[1], sys.argv[2])
