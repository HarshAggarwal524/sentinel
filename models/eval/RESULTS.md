# Sentinel — Baseline Evaluation Results

## Evaluation dataset
NAB (Numenta Anomaly Benchmark) — 58 files across 8 categories:
artificialNoAnomaly, artificialWithAnomaly, realAWSCloudwatch,
realAdExchange, realKnownCause, realTraffic, realTweets.

Evaluated using window-based scoring: a true anomaly window counts as
"caught" if at least one flagged point falls inside it.

## Baseline results (averaged across all 58 NAB files)

| Detector | Avg Precision | Avg Recall | Avg F1 | Avg FP/file |
|---|---|---|---|---|
| Seasonal-Hybrid ESD | 0.121 | 0.825 | **0.154** | 89.4 |
| Prophet | 0.070 | 0.841 | **0.110** | 82.7 |

Full per-file results logged to Weights & Biases:
https://wandb.ai/harshaggarwalofficial1-ggsipu/sentinel-anomaly-detection

## Interpretation

Both baselines show strong recall (~83%) but poor precision (~7-12%),
meaning they catch most real anomalies but generate many false alarms.
This is expected for simple statistical methods applied globally across
diverse time-series types without per-series learning.

**ESD outperforms Prophet overall** (F1: 0.154 vs 0.110), primarily
due to better precision. Both methods' weakness is false-positive rate —
the specific gap a trained ML model (Week 5) should close.

## Evaluation floor

Every future model built in this project must beat:
- **F1 > 0.154** (ESD baseline) on NAB to count as a genuine improvement
- W&B project tag for comparison: `sentinel-anomaly-detection`