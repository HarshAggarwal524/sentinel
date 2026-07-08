# Sentinel

Anomaly detection + chaos-engineering + human-approved auto-remediation for
containerized microservices.

> Status: Week 0 — repo scaffolding.

## Repo layout

- `ingestion/` — telemetry ingestion + feature extraction (Redis Streams consumer)
- `models/` — training code, experiments, evaluation harness
- `inference-service/` — anomaly scoring + explanation service
- `remediation-engine/` — rule-matching + human-approved remediation actions
- `frontend/` — Next.js dashboard
- `infra/` — Docker Compose, deployment configs
- `docs/` — architecture notes, write-ups, safety case log

## Running locally

```bash
docker compose up
```

(Not yet functional — first real services land end of Week 1.)