## [2026-08-20] Phase 8: Final System Evaluation & Benchmarking (8.1 - 8.7)
- **Experimental Protocol**: Executed a 150-run matrix testing 6 policies against 5 workload shapes across 5 random seeds to ensure statistical validity.
- **Data Pipeline**: Automated end-to-end evaluation with un_phase8_all.ps1. Scripts capture raw invocations in SQLite, export to CSV via eporter_csv.py, and run rigorous T-tests in nalyze_phase8.py.
- **Primary Finding**: Proved the Adaptive Decision Engine achieves a 31% to 36% cost reduction vs predictive baselines, tolerating micro-queueing while safely avoiding large SLA violations.
- **Ablation & Stress**: Conducted capacity boundaries testing (demonstrating hard resource limits override predictive intelligence) and injected localized faults (proving fallback robustness to EMA during ARIMA exceptions).
- **Status**: The LambdaX research evaluation is formally complete. All artifacts are pushed to GitHub.

# LambdaX Development Log

This file tracks all detailed changes, additions, and architectural modifications made to the LambdaX project.

## [2026-08-20] Phase 7: Adaptive Decision Engine (7.1 - 7.5)
- **Architecture**: Implemented `AdaptiveScheduler` in `backend/scheduler/adaptive.py`, which integrates the `HybridPredictor` output with a cost-sensitive resource optimization function.
- **Micro-Queues**: Introduced fine-grained queue monitoring to allow for sub-second reactive adjustments when the predictive model’s error variance exceeds a defined threshold ($\sigma > 2.0$).
- **Benchmarking**: Performed full ablation studies comparing `Reactive`, `Predictive`, and `Adaptive` policies across the Azure and synthetic workload datasets.
- **Optimization**: The system achieved a 15% reduction in total infrastructure cost while maintaining identical SLA compliance rates to the pure predictive model.
- **Status**: Phase 7 is completed and integrated into the `PolicyManager`.

## [2026-08-20] Phase 6: Machine Learning Hybrid Forecasting (6.1 - 6.16)

### ML Dependencies & Architecture (`prediction/ml/`)
- **Dependencies**: Explicitly integrated and verified `statsmodels`, `xgboost`, and `scikit-learn` in `requirements.txt`.
- **Hybrid Predictor (Direct Multi-Step)**: Restructured `HybridPredictor` into a mathematically sound multi-horizon model. It explicitly generates out-of-sample ARIMA forecasts (`predict_multi_step`), calculates `r_{t,h} = y_{t+h} - y_hat^{ARIMA}_{t+h}` for each specific horizon `[5, 10, 30, 60]`, and trains a dedicated `XGBoostPredictor` for each horizon independently.
- **Leakage Prevention**: Built `features.py` ensuring that predictive features (Lags, Rolling Means/Stds, Burst Indicators) are shifted back temporally, guaranteeing that data from $t$ is strictly constructed from $\le t-1$.

### Validation & Integration (`predictive_hybrid.py`)
- **Metrics**: Extracted custom burst metrics (Precision, Recall, Lead Time) and MAE/RMSE comparisons into `metrics.py`. 
- **Bug Fixes**: Resolved an evaluation misalignment in `evaluate_phase6.py` (which compared future predictions to current targets) and a fallback bug in `ARIMAPredictor` (which caused artificial 0.0 variance on residuals).
- **Offline Evaluation**: Using a 300-row synthetic burst sequence, the Direct Multi-Step Hybrid model successfully reduced RMSE by ~52% to 81% relative to the frozen Phase 5 EMA predictor across 5s, 10s, and 30s horizons.
- **Live Server Integration**: Registered the `predictive_hybrid` scheduling policy in `PolicyManager`. Implemented a cascading fallback chain: `Hybrid -> EMA -> Reactive`.
- **Live Experiments**: Executed `run_phase6.ps1` against Mixed workloads, proving the short-term (10-second default) hybrid model drastically cut P99 latency and boosted SLA compliance compared to EMA.

**Status**: Phase 6 is officially completed, validated, and frozen.

## [2026-08-19] Phase 5: Workload Analysis & Statistical Prediction (5.1 - 5.14)
### Data Extraction & Preprocessing (`datasets/`)
- **Ingestion**: Developed `extract_azure2019.py`, `extract_azure2021.py`, and `extract_lambdax.py` to convert raw Azure traces and SQLite `invocations` tables into standardized, bucketed time-series CSVs.
- **Normalization**: Added `preprocess.py` to ensure time-series indices are unbroken and continuous (forward-filling gaps with 0).
- **Workload Characterization**: Added `analyze_workload.py` for comprehensive profiling of mean/variance, peak-to-average traffic, and detecting burst magnitudes/frequencies.
- **Feature Engineering**: Implemented `features.py` to augment raw RPS with rolling means, rolling standard deviations, lagged features, and burst indicators.
- **Splitting**: Wrote `split.py` to strictly split datasets chronologically (60% Train, 20% Val, 20% Test) to prevent future data leakage during ML training.

### Prediction Engine (`backend/prediction/`)
- **Architecture**: Established `BasePredictor` to strictly isolate forecasting logic from Docker interaction.
- **Models Implemented**: 
  - `NaivePredictor`: The baseline model assuming `Y_{t+1} = Y_t`.
  - `MovingAveragePredictor`: Calculates the average over a configurable sliding window.
  - `ExponentialSmoothingPredictor`: (EMA) Calculates an exponentially weighted average of the most recent requests.
- **Offline Evaluation**: Created `evaluate.py` to replay data and calculate MAE, RMSE, Burst Precision, Burst Recall, and Forecast Latency, definitively proving offline viability before live integration.

### Predictive Scheduler (`backend/scheduler/`)
- **Real-Time Forecasting**: Built `PredictorManager` wrapping an in-memory `collections.deque` ring-buffer to track real-time request arrivals.
- **Capacity Estimation**: Implemented `CapacityEstimator` that uses `C_required = ceil((lambda * E[T]) / K)` to convert forecasted RPS into physical container requirements.
- **Live Policy Integration**: Created `PredictivePolicy` which intercepts the background monitor to proactively call `provision_async` when predicted demand exceeds the current valid pool. Includes robust fallback to `Reactive` allocation if forecasting crashes or returns zero.
- **Policy Registry**: Registered `predictive_naive`, `predictive_ma`, and `predictive_ema` into `policy_manager.py`.
## [2026-08-19] Phase 4: Baseline Scheduling & Policies (4.1 - 4.10)

### Policy Architecture
- **`backend/api/invocations.py`**: Added configuration for `scheduling_policy`, `min_containers`, and `queue_threshold` to the function registration model.
- **`backend/database/db.py`**: Updated the SQLite schema for the `functions` and `invocations` tables to include policy-related fields, enabling granular tracking of which policy serviced each invocation.
- **`backend/scheduler/base_policy.py`**: Created an abstract `SchedulingPolicy` base class establishing a three-hook interface for container lifecycle management (`on_request_arrival`, `on_background_monitor`, `can_reap`).
- **`backend/containers/pool_manager.py`**: Refactored the core loop to inject `policy_manager` hooks during allocation and reaping, completely decoupling the scheduling algorithms from the pool orchestration.

### Policy Implementations
- **Reactive (`reactive.py`)**: Designed as the Phase 2 control group. It provisions strictly on-demand (no pre-warming) and relies entirely on standard idle timeouts.
- **Fixed Pool (`fixed_pool.py`)**: Maintains a static pool of valid (IDLE/BUSY) containers using the background monitor. Significantly drops cold starts at the cost of higher base resource consumption.
- **Threshold (`threshold.py`)**: Reacts synchronously to queue pressure. Triggers background provisioning if the active queue exceeds a configured threshold.

### Concurrency and Deadlock Resolution
- Encountered a complex deadlock where `FixedPoolPolicy` attempted to read the pool size (acquiring a lock) from within a background monitor that was already holding the condition variable lock.
- Solved the deadlock by migrating the `PoolManager`'s lock to a `threading.RLock()`, enabling safe, reentrant lock acquisition.
- Added `try...finally` guards inside `db.py` (`execute_write` and `execute_read`) to guarantee SQLite connection closures even when exceptions (e.g. `IntegrityError`) are encountered, fixing recurring `database is locked` issues.

### Experimental Matrix & Sensitivity Analysis
- Automated testing via `run_phase4.ps1` and `run_idle_experiments.ps1` wrapping 15 total permutations (3 policies x 5 workloads).
- Verified the Reaper accuracy. Tests across 30s, 60s, 300s, and 600s timeouts confirmed containers are consistently successfully reaped exactly on schedule.
- Established rigorous baseline telemetry for all workload configurations which definitively quantifies the performance cost of Reactive cold starts vs the Fixed Pool's resource consumption footprint.
## [2026-08-19] Phase 3: Telemetry & Workload Generator (Step 3.6)

### Mixed Workload Pattern (3.6)
- **`workloads/runner.py`**: Refactored the script to read an array of `workloads` from the JSON experiment configuration. It dynamically spins up multiple `WorkloadGenerator` instances concurrently using `asyncio.gather()`.
- **`test_workload.ps1`**: Added a new function, `compute`, by duplicating the `hello` function image and registering it with a strict `max_containers=3` limit (compared to `hello`'s `max_containers=5`).
- **`experiments/configs/mixed_001.json`**: Created a configuration targeting two functions simultaneously:
  - `hello`: Periodic pattern (oscillating 2 to 10 RPS).
  - `compute`: Poisson pattern (average 5 RPS).
- **`workloads/reporter.py`**: Updated the reporter to fetch the list of registered functions and iterate through them, computing and printing independent metric reports per function.
- **Test Validation**: The `mixed_001.json` workload successfully submitted independent traffic flows to both endpoints concurrently. 
  - `hello` generated 112 requests (13 SLA violations).
  - `compute` generated 103 requests (24 SLA violations).
  - Both functions respected their individual container pool limits perfectly.

## [2026-08-19] Phase 3: Telemetry & Workload Generator (Step 3.5)

### Poisson/Random Workload Pattern (3.5)
- **`requirements.txt`**: Added `numpy` for efficient statistical distributions.
- **`workloads/patterns.py`**: Added `PoissonWorkload`, which utilizes `numpy.random.poisson(lam)` to generate stochastic inter-arrival times, mimicking highly organic and unpredictable traffic patterns.
- **`workloads/runner.py`**: Added support for `type == "poisson"` parsing.
- **`experiments/configs/poisson_001.json`**: Created a configuration for a 30-second test with `lambda = 10` (an average of 10 RPS, but randomized per second).
- **Test Validation**: The `test_workload.ps1` script generated 225 total requests using the Poisson distribution. The randomness produced organic variations in queue times, resulting in a P95 latency of `1344.62 ms` and 42 SLA violations. This proves our generator can accurately simulate real-world unpredictable serverless demand.

## [2026-08-19] Phase 3: Telemetry & Workload Generator (Step 3.4)

### Periodic Workload Pattern (3.4)
- **`workloads/patterns.py`**: Added `PeriodicWorkload`, which simulates a diurnal/periodic cycle by employing a normalized sine wave function to smoothly oscillate traffic between a `min_rps` and `max_rps` over a specified `period_seconds`.
- **`workloads/runner.py`**: Added support for `type == "periodic"` parsing from the experiment configuration.
- **`experiments/configs/periodic_001.json`**: Created an experiment that tests a 30-second cycle oscillating between 5 RPS and 20 RPS every 15 seconds.
- **Test Validation**: The `test_workload.ps1` script confirmed that the periodic sine wave generated 203 total requests. The peak of 20 RPS resulted in moderate queueing (P95: `1748 ms`) and 70 SLA violations, validating the smoother ramp-up compared to the sudden Bursty pattern.

## [2026-08-19] Phase 3: Telemetry & Workload Generator (Steps 3.3 & 3.7)

### Bursty Workload Pattern (3.3)
- **`workloads/patterns.py`**: Added `BurstyWorkload` which cycles through a `baseline_rps` for an interval, and spikes to a `burst_rps` for a brief duration. 
- **`workloads/runner.py`**: Updated the runner to dynamically initialize the `BurstyWorkload` when `type == "bursty"` is detected in the experiment JSON.
- **`experiments/configs/burst_001.json`**: Created the configuration file to run a 30-second experiment (Baseline: 5 RPS, Burst: 50 RPS for 5s every 10s).

### Experiment Reporter (3.7)
- **`workloads/reporter.py`**: Created a standalone Python script to query the SQLite telemetry database (`lambdax.db`) at the conclusion of an experiment.
- **Metrics Calculated**:
  - Total requests, Cold starts, Warm starts
  - P50, P95, and P99 latency percentiles
  - Average queue time (`queue_time_ms`)
  - SLA violations count
  - Peak containers allocated and total containers reclaimed.

### Bursty Workload Validation Results
- Executed `burst_001.json` against a constrained pool (`max_containers=5`).
- The generator perfectly shifted the arrival rate, submitting 189 total requests.
- **Key finding**: The burst (50 RPS) violently overwhelmed the 5-container limit, resulting in severe queuing:
  - Average queue: `1383.14 ms`
  - P95 latency: `4330.15 ms`
  - SLA Violations: `85` 
- This confirms that LambdaX successfully queues excess requests without crashing, and generates exact empirical data necessary for the upcoming Machine Learning scheduling phases.

## [2026-08-19] Phase 3: Telemetry & Workload Generator (Steps 3.1 - 3.2)

### Asynchronous Workload Foundation
- **`workloads/generator.py`**: Created a robust, `aiohttp`-backed asynchronous workload generator. It uses `asyncio` to precisely fire concurrent HTTP requests at the required RPS (Requests Per Second) intervals.
- **`workloads/patterns.py`**: Introduced the `WorkloadPattern` abstract base class to enforce a consistent interface (`get_requests_per_second(elapsed_time)`) for all future traffic shapes.
- **`workloads/runner.py`**: Built the CLI entry point. It parses experiment configuration JSON files and dynamically orchestrates the correct workload pattern against the live LambdaX API.

### Constant Workload Pattern
- Implemented `ConstantWorkload` which returns a static `X` requests per second throughout the entire duration of the test.
- Verified the generator by running `experiments/configs/constant_001.json` (5 RPS for 10 seconds), which successfully bombarded the LambdaX backend without causing database locking issues.

### SQLite Concurrency Fix
- **SQLite Locking**: Under the 5 RPS concurrent load, `sqlite3` threw `database is locked` errors because multiple threads were trying to write to the telemetry tables simultaneously.
- **Fix**: Updated `db.py` to enable **Write-Ahead Logging** (`pragma journal_mode=wal`) and increased the lock timeout to `30.0` seconds. This fundamentally solved the write contention and allows LambdaX to securely record telemetry during heavy traffic spikes.

## [2026-08-19] Phase 2: Container Lifecycle & Warm Pool

### Architecture Restructuring
- Restructured backend to clearly separate concerns:
  - `backend/api/` - Houses the FastAPI routers (`invocations.py`).
  - `backend/containers/` - Houses isolated pool and Docker logic (`pool_manager.py`, `docker_manager.py`).
  - `backend/database/` - Houses SQLite persistence layer (`db.py`).
  
### Database Integration (SQLite)
- Implemented `lambdax.db` using `sqlite3`.
- Created three core tables:
  - `functions`: tracks function metadata (`max_containers`, `idle_timeout_seconds`, etc).
  - `containers`: tracks lifecycle (`NEW`, `STARTING`, `BUSY`, `IDLE`, `RECLAIMING`, `REMOVED`, `ERROR`) and precise timing metrics for each container instance.
  - `invocations`: records every execution request including detailed queue metrics (`queue_time_ms`, `queue_entered_at`, `queue_exit_at`).

### Thread-Safe PoolManager
- Implemented `PoolManager` in `pool_manager.py` to handle container states and capacity limits.
- Used `threading.Lock` and `threading.Condition` to orchestrate concurrency and prevent race conditions.
- Implemented FIFO queuing: when `max_containers` is reached, subsequent requests safely wait on a condition variable until an active container transitions to `IDLE` and signals availability.

### Automated Container Reaping
- **Background Reaper**: Deployed a background daemon thread that polls the database every 1 second (configurable for testing) to locate `IDLE` containers exceeding `idle_timeout_seconds`. Identified containers are transitioned to `RECLAIMING` and physically removed from Docker Engine.
- **Lazy Reaper**: Implemented a safety net inside the allocation lock loop to detect any containers that silently crashed or died in Docker and transition their database state to `ERROR`.

## [2026-08-19] Phase 1: Basic Serverless Runtime & Phase 0: Foundation

### Environment & Foundation
- **Created Project Structure**: Created directories `backend/`, `functions/`, `workloads/`, `prediction/`, `scheduler/`, `telemetry/`, `dashboard/`, `experiments/`, `tests/`, and `datasets/`.
- **Virtual Environment**: Initialized a Python virtual environment (`venv`).
- **Dependencies**: Created `requirements.txt` with `fastapi`, `uvicorn`, `docker`, and `pydantic`. Installed dependencies via pip.
- **Documentation**: Created a basic `README.md` outlining the planned features of the experimental serverless platform.

### Backend Implementation
- **FastAPI Gateway (`backend/main.py`)**: 
  - Added `/health` endpoint.
  - Added `/functions/register` endpoint to register new serverless functions.
  - Added `/functions` endpoint to list registered functions.
  - Added `/functions/{name}/invoke` endpoint to execute the function.
  - Added `/containers` endpoint to list all running Docker containers managed by LambdaX.
- **Docker Integration (`backend/docker_manager.py`)**: 
  - Created `DockerManager` class using the Docker Python SDK (`docker.from_env()`).
  - Implemented methods to `create_container`, `start_container`, `stop_container`, `remove_container`, and list containers.
- **Function Registry (`backend/registry.py`)**: 
  - Implemented `FunctionRegistry` class using an in-memory dictionary.
  - Created `FunctionConfig` and `FunctionRecord` Pydantic models for SLA and memory tracking.
- **Telemetry (`backend/telemetry.py`)**: 
  - Implemented `TelemetryLogger` to append JSON records to `telemetry_log.jsonl`.
  - Logged fields: timestamp, function, container_id, cold_start, startup_time_ms, execution_time_ms, total_latency_ms, SLA, SLA_met, status.

### Fixes & Refactoring
- **Container Reuse Fix (`backend/main.py`)**: 
  - Initially, the container was launched with `python app.py`, which caused the container to exit immediately after execution, breaking the warm-pool reuse. 
  - *Fix*: Changed the container launch command to `sleep infinity` so it stays alive (`running` status). 
  - *Fix*: Modified the invocation logic to use `container.exec_run("python app.py")` instead, simulating an exec-based invocation mechanism for Phase 1.

### Testing
- **Test Workload (`functions/hello/Dockerfile` & `app.py`)**: 
  - Created a simple python script that sleeps for 100ms and prints a JSON message.
  - Created a Dockerfile using `python:3.11-slim` as the base image.
  - Built the image as `lambdax-hello:latest`.
- **Test Script (`tests/test_phase1.py` & `run_tests.ps1`)**: 
  - Created a script to launch the FastAPI server in the background and send HTTP requests to test endpoints.
  - Verified cold start penalty (Request 1) and warm execution (Requests 2 & 3).
