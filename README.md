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

## Phase 8 Evaluation Results
In a 150-run rigorously paired benchmark matrix comparing the Adaptive engine against standard industry baselines:
- **Cost Reduction**: The Adaptive policy reduced total infrastructure cost (container-seconds) by **31.3%** compared to Reactive, and **36.0%** compared to naive ML-Predictive policies.
- **Latency Optimization**: The Adaptive policy reduced cold start rates by **59.2%** compared to Reactive.
- **Pareto Efficiency**: The Adaptive policy successfully identified the mathematical Pareto-frontier, demonstrating that it can intelligently tolerate a minor SLA dip (micro-queueing) to avoid massive infrastructure over-provisioning when ML forecasting variance is high.

All raw data, validation tests, capacity stress tests, and fault-injection analyses are available in `experiments/results/phase8/`.

## Running the Platform
1. **Prerequisites**: Python 3.11+, Docker Engine, PowerShell.
2. **Environment**: `python -m venv venv` followed by `pip install -r requirements.txt`.
3. **Run Server**: `Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000"`
4. **Execute Tests**: Use `run_tests.ps1` for basic validation or `run_phase8_all.ps1` to execute the full evaluation suite.
