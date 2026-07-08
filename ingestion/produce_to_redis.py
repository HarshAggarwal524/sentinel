import time
import requests
import redis
from prometheus_client.parser import text_string_to_metric_families

OTEL_METRICS_URL = "http://localhost:8889/metrics"
STREAM_NAME = "raw-metrics"

r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def fetch_metrics_text():
    response = requests.get(OTEL_METRICS_URL, timeout=10)
    response.raise_for_status()
    return response.text


def push_metrics_to_stream(metrics_text):
    count = 0
    for family in text_string_to_metric_families(metrics_text):
        for sample in family.samples:
            service_name = sample.labels.get("service", "unknown")
            r.xadd(STREAM_NAME, {
                "service_name": service_name,
                "metric_name": sample.name,
                "value": str(sample.value),
                "labels": str(sample.labels),
            })
            count += 1
    return count


if __name__ == "__main__":
    print(f"Pushing metrics into Redis stream '{STREAM_NAME}' every 15 seconds...")
    while True:
        text = fetch_metrics_text()
        n = push_metrics_to_stream(text)
        print(f"Pushed {n} entries into the stream.")
        time.sleep(15)