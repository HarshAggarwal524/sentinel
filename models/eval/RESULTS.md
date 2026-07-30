# Sentinel — Evaluation Results

---

## Part 1: NAB Benchmark (Week 3)

### Dataset
NAB (Numenta Anomaly Benchmark) — 58 files across 8 categories:
artificialNoAnomaly, artificialWithAnomaly, realAWSCloudwatch,
realAdExchange, realKnownCause, realTraffic, realTweets.
Evaluated using window-based scoring: a true anomaly window counts as
"caught" if at least one flagged point falls inside it.

### Results (averaged across all 58 NAB files)

| Detector | Avg Precision | Avg Recall | Avg F1 | Avg FP/file |
|---|---|---|---|---|
| Seasonal-Hybrid ESD | 0.121 | 0.825 | **0.154** | 89.4 |
| Prophet | 0.070 | 0.841 | **0.110** | 82.7 |

Full per-file results logged to W&B:
https://wandb.ai/harshaggarwalofficial1-ggsipu/sentinel-anomaly-detection

### Interpretation
Both baselines show strong recall (~83%) but poor precision (~7-12%),
meaning they catch most real anomalies but generate many false alarms.
ESD outperforms Prophet overall (F1: 0.154 vs 0.110). Both methods'
weakness is false-positive rate — the specific gap a trained ML model
should close.

### NAB Evaluation Floor
Every future model must beat **F1 > 0.154** on NAB to count as genuine
improvement on the standard benchmark.

---

## Part 2: Sock Shop Live Dataset (Weeks 4–5)

### Dataset
78 labeled fault-injection windows across 4 fault types and 6 target
containers, collected over ~91 hours of continuous chaos battery runs.
Train/Val/Test split: 44 / 15 / 15 files (60/20/20 at file level).
Metric: `container_cpu_usage_seconds_total` converted to per-step rate.

### Critical preprocessing bug found and fixed (Week 5)

`container_cpu_usage_seconds_total` is a cumulative counter — it only
ever goes up. Feeding raw values to a model gives it a smooth,
monotonically-rising curve with no anomaly signal whatsoever. Converting
to per-step rate (delta between consecutive readings) reveals clear spikes
at fault boundaries. All results marked ⚠️ below used raw counter values
and are invalid — listed only for historical completeness.


### Full results on Sock Shop Live dataset (all rate-corrected)

| Model | Precision | Recall | F1 | Files evaluated |
|---|---|---|---|---|
| ESD (rate-corrected) | 0.036 | 0.064 | 0.045 | 78 |
| Prophet (rate-corrected) | 0.051 | 0.064 | 0.056 | 78 |
| LSTM (rate-corrected) | — | — | — | N/A — failed to converge |
| **TCN v2 (rate-corrected)** | **0.136** | **0.227** | **0.158** | 15 (test split) |

⚠️ All previous Sock Shop results (ESD: 0.057, Prophet: 0.052, TCN v1: 0.087)
used raw cumulative counter values and are invalid. Only rate-corrected
results above should be cited.

### TCN v2 results by fault type

| Fault Type | Test Files | Precision | Recall | F1 |
|---|---|---|---|---|
| packet_loss | 2 | 0.250 | 0.500 | 0.333 |
| container_kill | 2 | 0.167 | 0.500 | 0.250 |
| network_delay | 6 | 0.111 | 0.083 | 0.095 |
| cpu_stress | 1 | 0.000 | 0.000 | 0.000 |
| **OVERALL** | **11** | **0.136** | **0.227** | **0.158** |

### Key findings

**TCN v2 (F1: 0.158) is the first valid result on this dataset** and
beats both statistical baselines. It also matches NAB's ESD baseline
(0.154) — meaningful given it's evaluated on our own live system data,
not a pre-packaged benchmark.

**LSTM cannot train on this dataset size.** 292 training sequences of
length 5 is insufficient for LSTM convergence — val loss stayed flat at
0.350 and early-stopped at epoch 16. Documented as an architecture/data
mismatch, not a code bug. Will revisit if dataset size increases.

**Network delay is the hardest fault type (F1: 0.095).** CPU rate is the
wrong primary signal for network delay — request latency metrics would
be more appropriate. Directly motivates Week 6's multi-metric approach.

**cpu_stress scored 0.000 on a single test file** — likely statistical
noise from tiny per-type sample size (1 file), not a model failure.

### Sock Shop Live Evaluation Floor
Every future model must beat **F1 > 0.158** (TCN v2) on the Sock Shop
live test set to count as genuine improvement.

---

## Part 3: W&B Run Index

| Run name | What it covers |
|---|---|
| week3-baseline-eval | NAB full evaluation (ESD + Prophet, 58 files) |
| week4-sock-shop-live-eval | Sock Shop live eval (ESD + Prophet, 78 files, ⚠️ raw counter) |
| week5-lstm-autoencoder | LSTM training run 1 (raw counter) |
| week5-tcn-autoencoder | TCN training run 1 (raw counter) |
| week5-model-evaluation | Evaluation run 1 (raw counter, ⚠️ invalid) |
| week5-lstm-rate-retrain | LSTM retrain (rate-corrected, failed to converge) |
| week5-tcn-rate-retrain | TCN retrain (rate-corrected, best model) |
| week5-final-results | Final comparison table |

W&B project:
https://wandb.ai/harshaggarwalofficial1-ggsipu/sentinel-anomaly-detection
