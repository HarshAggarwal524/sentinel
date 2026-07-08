import ast
import redis
import psycopg2

STREAM_NAME = "raw-metrics"
GROUP_NAME = "sentinel-consumers"
CONSUMER_NAME = "consumer-1"

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",  # must match your .env value
)


def process_entries(conn, entries):
    cur = conn.cursor()
    for stream_name, messages in entries:
        for message_id, fields in messages:
            try:
                labels_dict = ast.literal_eval(fields.get("labels", "{}"))
            except (ValueError, SyntaxError):
                labels_dict = {}

            cur.execute(
                """
                INSERT INTO metrics (time, service_name, metric_name, value, labels)
                VALUES (NOW(), %s, %s, %s, %s)
                """,
                (
                    fields.get("service_name", "unknown"),
                    fields.get("metric_name", "unknown"),
                    float(fields.get("value", 0)),
                    psycopg2.extras.Json(labels_dict),
                ),
            )
            # Acknowledge only after successfully writing to the database
            r.xack(STREAM_NAME, GROUP_NAME, message_id)
    conn.commit()
    cur.close()


if __name__ == "__main__":
    import psycopg2.extras

    conn = psycopg2.connect(**DB_CONFIG)
    print(f"Consumer '{CONSUMER_NAME}' listening on stream '{STREAM_NAME}'...")

    while True:
        entries = r.xreadgroup(
            GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=100, block=5000
        )
        if entries:
            process_entries(conn, entries)
            total = sum(len(messages) for _, messages in entries)
            print(f"Processed and saved {total} entries.")