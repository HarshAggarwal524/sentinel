# Sentinel — Dataset Documentation

## Overview

Sentinel uses two distinct datasets for evaluation:

1. **NAB (Numenta Anomaly Benchmark)** — an external, publicly available benchmark
2. **Sock Shop Live Dataset** — our own labeled dataset generated from real fault injections on our live demo system

This document covers the Sock Shop Live Dataset in full detail.

---

## Sock Shop Live Dataset

### Why we built it

NAB proves our detectors work on a standard academic benchmark. It doesn't prove they work on the specific kind of data Sentinel actually watches — containerized microservices, Docker networking, real infrastructure metrics. The Sock Shop Live Dataset fills that gap.

### How it was generated

**Step 1 — Live system setup**
Sock Shop (a pre-built fake e-commerce microservices application, ~14 containers) ran continuously on a local Docker Compose stack. Locust generated continuous fake user traffic (10 simulated users) against it throughout the entire collection period.

**Step 2 — Metric collection**
The OpenTelemetry Collector scraped metrics from every Sock Shop container every 15 seconds, flowing through Redis Streams into TimescaleDB. The primary metric used for labeling is `container_cpu_usage_seconds_total`, recorded per container via cAdvisor.

**Step 3 — Fault injection**
Pumba (a Docker chaos engineering tool) was used to inject four types of controlled faults into six target containers, on a randomized schedule (30–90 minute gaps between experiments):

**Fault types:**
- `cpu_stress` — infinite loop pinning CPU to ~100% for 90 seconds
- `network_delay` — 300ms added latency via Pumba netem for 90 seconds
- `packet_loss` — 40% packet drop rate via Pumba netem for 90 seconds
- `container_kill` — abrupt container restart via `docker compose restart`

**Target containers:**
- `sentinel-catalogue-1`, `sentinel-carts-1`, `sentinel-orders-1`
- `sentinel-front-end-1`, `sentinel-payment-1`, `sentinel-shipping-1`

**Step 4 — Ground truth logging**
Every experiment was logged to a `fault_injections` PostgreSQL table with exact UTC start and end timestamps, experiment type, target container, and parameters. This table is the answer key for evaluation.

**Step 5 — Labeling join**
`ingestion/build_labeled_dataset.py` joins the fault log against the metrics table: for each fault, it extracts a 20-minute metric window (10 minutes before → 10 minutes after the fault) for the target container, and labels the actual fault duration as the anomaly window — producing NAB-compatible CSV + labels.json files.

### Collection period

- **Start:** 2026-07-23 16:49 UTC
- **End:** 2026-07-27 08:09 UTC
- **Total calendar span:** ~91 hours (minus ~5 hours outage, see below)

### Known data quality issues

**Ingestion pipeline outage (~5 hours, 2026-07-23 12:40–17:44 UTC)**
The ingestion scripts (`produce_to_redis.py`, `consume_from_redis.py`, `compute_features.py`) crashed due to missing retry/reconnect logic on transient connection failures. Fixed by adding try/except with reconnect logic to all three scripts. 4 fault injections (IDs 7-10) that occurred during this window were identified via gap analysis and excluded from the labeled dataset.

Full incident report: see `docs/pipeline-incident-2026-07-23.md`

### Dataset statistics

| Metric | Value |
|---|---|
| Total fault injections logged | 128 |
| Usable labeled windows | 78 |
| Skipped (insufficient metrics) | 18 |
| Fault types | 4 |
| Target containers | 6 |
| Metric scrape interval | 15 seconds |
| Window size per fault | 20 minutes (±10 min) |

**Fault type distribution:**
| Type | Count |
|---|---|
| cpu_stress | 27 |
| network_delay | 25 |
| container_kill | 25 |
| packet_loss | 19 |

**Target container distribution:**
| Container | Count |
|---|---|
| sentinel-catalogue-1 | 29 |
| sentinel-carts-1 | 16 |
| sentinel-payment-1 | 16 |
| sentinel-orders-1 | 12 |
| sentinel-front-end-1 | 12 |
| sentinel-shipping-1 | 11 |

### Baseline evaluation results on this dataset

| Detector | Avg Precision | Avg Recall | Avg F1 |
|---|---|---|---|
| Seasonal-Hybrid ESD | 0.051 | 0.077 | 0.057 |
| Prophet | 0.048 | 0.064 | 0.052 |

**Why these scores are low (and expected):** each evaluation window is only ~80 data points (20 minutes at 15-second intervals). ESD and Prophet both require substantial historical context to establish a "normal" baseline — on short windows, they're effectively working without history. This is the specific gap that trained ML models (Week 5) are designed to close: a model trained on weeks of historical data brings that context with it, rather than needing it within the evaluation window.

Full results logged to W&B: `sentinel-anomaly-detection` project, tag `sock-shop-live`.

### Reproducibility

To regenerate this dataset from scratch:
1. Run Sock Shop + ingestion pipeline (see `docs/week1-build-log.md`)
2. Run `python infra/chaos_battery.py` for 3+ days with Locust generating traffic
3. Run `python ingestion/build_labeled_dataset.py`

The `fault_injections` table in TimescaleDB serves as the permanent ground truth log.