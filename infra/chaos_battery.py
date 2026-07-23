import random
import time
import psycopg2
import psycopg2.extras
import subprocess
from datetime import datetime, timezone

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",
)

# All Sock Shop services we're willing to target
TARGETS = [
    "sentinel-catalogue-1",
    "sentinel-carts-1",
    "sentinel-orders-1",
    "sentinel-front-end-1",
    "sentinel-payment-1",
    "sentinel-shipping-1",
]

# How long to wait between experiments (seconds)
MIN_GAP = 1800   # 30 minutes minimum of normal traffic between faults
MAX_GAP = 5400   # 90 minutes maximum


def log_start(conn, experiment_type, target, parameters=None, notes=None):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO fault_injections
            (experiment_type, target_container, start_time, parameters, notes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            experiment_type,
            target,
            datetime.now(timezone.utc),
            psycopg2.extras.Json(parameters or {}),
            notes,
        ),
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return row_id


def log_end(conn, row_id):
    cur = conn.cursor()
    cur.execute(
        "UPDATE fault_injections SET end_time = %s WHERE id = %s;",
        (datetime.now(timezone.utc), row_id),
    )
    conn.commit()
    cur.close()


def do_cpu_stress(conn, target, duration=90):
    row_id = log_start(conn, "cpu_stress", target,
                       parameters={"duration_seconds": duration})
    proc = subprocess.Popen(
        ["docker", "exec", target, "sh", "-c", "while true; do :; done"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(duration)
    proc.terminate()
    service = target.replace("sentinel-", "").rsplit("-", 1)[0]
    subprocess.run(["docker", "compose", "restart", service], capture_output=True)
    log_end(conn, row_id)


def do_network_delay(conn, target, delay_ms=300, duration=90):
    row_id = log_start(conn, "network_delay", target,
                       parameters={"delay_ms": delay_ms, "duration_seconds": duration})
    proc = subprocess.Popen(
        ["pumba", "netem", "--duration", f"{duration}s",
         "delay", "--time", str(delay_ms), target],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(duration + 5)
    proc.terminate()
    log_end(conn, row_id)


def do_packet_loss(conn, target, loss_percent=40, duration=90):
    row_id = log_start(conn, "packet_loss", target,
                       parameters={"loss_percent": loss_percent, "duration_seconds": duration})
    proc = subprocess.Popen(
        ["pumba", "netem", "--duration", f"{duration}s",
         "loss", "--percent", str(loss_percent), target],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(duration + 5)
    proc.terminate()
    log_end(conn, row_id)


def do_container_kill(conn, target):
    row_id = log_start(conn, "container_kill", target)
    service = target.replace("sentinel-", "").rsplit("-", 1)[0]
    subprocess.run(["docker", "compose", "restart", service], capture_output=True)
    time.sleep(10)
    log_end(conn, row_id)


EXPERIMENTS = [do_cpu_stress, do_network_delay, do_packet_loss, do_container_kill]

if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    experiment_count = 0

    print("Chaos battery started. Running indefinitely until you Ctrl+C.")
    print(f"Gap between experiments: {MIN_GAP//60}–{MAX_GAP//60} minutes\n")

    while True:
        # Pick a random experiment and a random target
        experiment_fn = random.choice(EXPERIMENTS)
        target = random.choice(TARGETS)
        experiment_count += 1

        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Experiment #{experiment_count}: {experiment_fn.__name__} on {target}")

        try:
            experiment_fn(conn, target)
            print(f"[{now}] Done. Total experiments logged: {experiment_count}")
        except Exception as e:
            print(f"[{now}] Failed: {e} — skipping, continuing battery")

        # Wait a random gap of normal traffic before the next fault
        gap = random.randint(MIN_GAP, MAX_GAP)
        next_time = datetime.now().strftime("%H:%M:%S")
        print(f"[{next_time}] Sleeping {gap//60} minutes until next experiment...\n")
        time.sleep(gap)