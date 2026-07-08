import time
import requests
import psycopg2
from prometheus_client.parser import text_string_to_metric_families

OTEL_METRICS_URL = "http://localhost:8889/metrics"
DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",  # must match your .env value
)


def fetch_metrics_text():
    response = requests.get(OTEL_METRICS_URL, timeout=10)
    response.raise_for_status()
    return response.text


def write_metrics_to_db(conn, metrics_text):
    cur = conn.cursor()
    count = 0
    for family in text_string_to_metric_families(metrics_text):
        for sample in family.samples:
            service_name = sample.labels.get("service", "unknown")
            cur.execute(
                """
                INSERT INTO metrics (time, service_name, metric_name, value, labels)
                VALUES (NOW(), %s, %s, %s, %s)
                """,
                (service_name, sample.name, sample.value, psycopg2.extras.Json(sample.labels)),
            )
            count += 1
    conn.commit()
    cur.close()
    return count


if __name__ == "__main__":
    import psycopg2.extras

    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected to database. Starting to copy metrics every 15 seconds...")
    while True:
        text = fetch_metrics_text()
        n = write_metrics_to_db(conn, text)
        print(f"Wrote {n} metric rows into the notebook.")
        time.sleep(15)