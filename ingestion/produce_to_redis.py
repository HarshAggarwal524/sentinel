import time
import requests
import redis
from prometheus_client.parser import text_string_to_metric_families

OTEL_METRICS_URL = "http://localhost:8889/metrics"
STREAM_NAME = "raw-metrics"


def get_redis_client():
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def fetch_metrics_text():
    response = requests.get(OTEL_METRICS_URL, timeout=10)
    response.raise_for_status()
    return response.text


def push_metrics_to_stream(r, metrics_text):
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
    r = get_redis_client()
    print(f"Pushing metrics into Redis stream '{STREAM_NAME}' every 15 seconds...")

    while True:
        try:
            text = fetch_metrics_text()
            n = push_metrics_to_stream(r, text)
            print(f"Pushed {n} entries into the stream.")

        except requests.exceptions.RequestException as e:
            # Covers ReadTimeout, ConnectionError, HTTPError (e.g. Collector down or slow)
            print(f"[warn] Could not reach OTel Collector: {e} — retrying in 5s")
            time.sleep(5)
            continue  # skip the normal 15s sleep, retry sooner

        except redis.exceptions.RedisError as e:
            print(f"[warn] Redis error: {e} — reconnecting in 5s")
            time.sleep(5)
            try:
                r = get_redis_client()
            except Exception as e2:
                print(f"[warn] Redis reconnect failed: {e2}")
            continue

        except Exception as e:
            print(f"[warn] Unexpected error: {e} — continuing in 5s")
            time.sleep(5)
            continue

        time.sleep(15)