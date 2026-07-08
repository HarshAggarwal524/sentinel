import time
import psycopg2

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",
)

WINDOWS = {
    "5min": "5 minutes",
    "15min": "15 minutes",
    "1hr": "1 hour",
}


def compute_and_store_features(conn):
    cur = conn.cursor()

    # Find every distinct (service, metric) pair we currently have data for
    cur.execute("SELECT DISTINCT service_name, metric_name FROM metrics;")
    pairs = cur.fetchall()

    total_written = 0
    for service_name, metric_name in pairs:
        for window_label, interval in WINDOWS.items():
            cur.execute(
                f"""
                SELECT AVG(value), STDDEV(value)
                FROM metrics
                WHERE service_name = %s
                  AND metric_name = %s
                  AND time > NOW() - INTERVAL '{interval}';
                """,
                (service_name, metric_name),
            )
            avg_value, stddev_value = cur.fetchone()

            if avg_value is None:
                continue  # no data in this window yet, skip

            cur.execute(
                """
                INSERT INTO metric_features
                    (time, service_name, metric_name, window_label, avg_value, stddev_value)
                VALUES (NOW(), %s, %s, %s, %s, %s);
                """,
                (service_name, metric_name, window_label, avg_value, stddev_value),
            )
            total_written += 1

    conn.commit()
    cur.close()
    return total_written


if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    print("Computing rolling features every 60 seconds...")
    while True:
        n = compute_and_store_features(conn)
        print(f"Wrote {n} feature rows.")
        time.sleep(60)