# LambdaX

LambdaX is an experimental serverless computing platform designed to evaluate and optimize the trade-offs between cold-start latency and infrastructure cost through intelligent container pool scheduling. 

## Overview
Unlike standard reactive serverless platforms (which spawn containers strictly on-demand, causing high cold starts) or static provisioned platforms (which keep containers warm indefinitely, wasting resources), LambdaX uses a **Closed-Loop Adaptive Scheduling Engine**. It combines time-series Machine Learning forecasting (ARIMA + XGBoost) with a dynamic cost-model to mathematically optimize the resource-latency Pareto frontier.

## Architecture and Phases
The project was developed in 8 rigorous phases:

- **Phase 1**: Basic Serverless Runtime (FastAPI + Docker API)
- **Phase 2**: Container Lifecycle & Warm Pool Management
- **Phase 3**: Concurrency, SQLite Telemetry, & Stochastic Workload Generators (Poisson, Periodic, Bursty)
- **Phase 4**: Baseline Scheduling Policies (Reactive, Fixed Pool, Threshold)
- **Phase 5**: Workload Analysis & Statistical Prediction (EMA, Moving Averages)
- **Phase 6**: Machine Learning Hybrid Forecasting (Multi-Horizon XGBoost + ARIMA)
- **Phase 7**: Adaptive Decision Engine (Micro-queueing + SLA/Cost Optimization)
- **Phase 8**: Final System Evaluation & Benchmarking
- **Phase 9**: Model Predictive Control (MPC) Baseline & Comparison
- **Phase 10**: Live Control Plane Dashboard (React/Vite)

## Phase 8 & 9 Evaluation Results (Empirical)
In a 150-run rigorously paired benchmark matrix comparing the Adaptive engine against standard industry baselines:
- **Cost Reduction**: The Adaptive policy reduced total infrastructure cost (container-seconds) by **25.8%** compared to Reactive, **39.5%** compared to EMA Predictive, and **23.0%** against the optimized Hybrid ML Predictive baseline.
- **Latency Optimization**: The Adaptive policy reduced cold start rates by **26.3%** compared to Reactive and **17.9%** compared to the Hybrid model.
- **Pareto Efficiency**: The Adaptive policy successfully identified the mathematical Pareto-frontier, intentionally tolerating a minor 11.8% dip in strict SLA compliance (via micro-queueing) to avoid massive infrastructure over-provisioning when ML forecasting variance was high. (Statistically significant at $p < 0.01$).
- **MPC Superiority**: In Phase 9, the Adaptive policy structurally outperformed a classical Model Predictive Control (MPC) baseline. MPC suffered from high computational overhead and 30-40% higher container costs due to aggressively over-provisioning to eliminate all predicted SLA violations.

*Note on Configuration: The default `adaptive` policy in `config.json` uses `enable_priority: false` to ensure fair apples-to-apples comparison against baselines. Priority-based preemption is specifically activated during priority ablation tests.*

All raw data, validation tests, capacity stress tests, and fault-injection analyses are available in `experiments/results/phase8/`.

## Running the Platform
1. **Prerequisites**: Python 3.11+, Docker Engine, PowerShell.
2. **Environment**: `python -m venv venv` followed by `pip install -r requirements.txt`.
3. **Run Server**: `Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000"`
4. **Execute Tests**: Use `run_tests.ps1` for basic validation or `run_phase8_all.ps1` to execute the full evaluation suite.
