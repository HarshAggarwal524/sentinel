import ast
import time
import redis
import psycopg2
import psycopg2.extras

STREAM_NAME = "raw-metrics"
GROUP_NAME = "sentinel-consumers"
CONSUMER_NAME = "consumer-1"

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",  # must match your .env value
)


def get_redis_client():
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


def get_db_conn():
    return psycopg2.connect(**DB_CONFIG)


def process_entries(conn, r, entries):
    """Insert all entries, commit, and only THEN ack — so a failed commit
    never results in an entry being marked done without actually being saved."""
    cur = conn.cursor()
    acked_ids = []

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
            acked_ids.append(message_id)

    conn.commit()  # commit FIRST
    cur.close()

    for message_id in acked_ids:  # only ack what actually made it to the DB
        r.xack(STREAM_NAME, GROUP_NAME, message_id)

    return len(acked_ids)


if __name__ == "__main__":
    r = get_redis_client()
    conn = get_db_conn()
    print(f"Consumer '{CONSUMER_NAME}' listening on stream '{STREAM_NAME}'...")

    while True:
        try:
            entries = r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=100, block=5000
            )
            if entries:
                total = process_entries(conn, r, entries)
                print(f"Processed and saved {total} entries.")

        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            print(f"[warn] Redis connection issue: {e} — reconnecting in 5s")
            time.sleep(5)
            try:
                r = get_redis_client()
            except Exception as e2:
                print(f"[warn] Redis reconnect failed: {e2}")

        except psycopg2.OperationalError as e:
            print(f"[warn] Postgres connection dropped: {e} — reconnecting in 5s")
            time.sleep(5)
            try:
                conn = get_db_conn()
            except Exception as e2:
                print(f"[warn] Postgres reconnect failed: {e2}")

        except Exception as e:
            # Catch-all so one unexpected error doesn't kill an unattended multi-day run
            print(f"[warn] Unexpected error: {e} — continuing in 5s")
            time.sleep(5)