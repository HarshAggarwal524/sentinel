import subprocess
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
import time
import random

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",
)

# The containers we'll target — these are Sock Shop's core services
TARGETS = [
    "sentinel-catalogue-1",
    "sentinel-carts-1",
    "sentinel-orders-1",
    "sentinel-front-end-1",
    "sentinel-payment-1",
]


def log_experiment_start(conn, experiment_type, target, parameters=None, notes=None):
    """Write the start of an experiment to the database. Returns the row id."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO fault_injections (experiment_type, target_container, start_time, parameters, notes)
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


def log_experiment_end(conn, row_id):
    """Fill in the end_time once the experiment finishes."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE fault_injections SET end_time = %s WHERE id = %s;",
        (datetime.now(timezone.utc), row_id),
    )
    conn.commit()
    cur.close()


def run_cpu_stress(conn, target, duration_seconds=60):
    """Pin a container's CPU near 100% for a set duration."""
    print(f"[CPU STRESS] Starting on {target} for {duration_seconds}s")
    row_id = log_experiment_start(
        conn, "cpu_stress", target,
        parameters={"duration_seconds": duration_seconds},
        notes="Infinite loop stress via shell"
    )
    # Run an infinite loop inside the container for the duration
    proc = subprocess.Popen(
        ["docker", "exec", target, "sh", "-c", "while true; do :; done"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(duration_seconds)
    proc.terminate()
    # Restart the container cleanly to kill any lingering stress processes
    subprocess.run(["docker", "compose", "restart", target.replace("sentinel-", "").rsplit("-", 1)[0]],
                   capture_output=True)
    log_experiment_end(conn, row_id)
    print(f"[CPU STRESS] Done on {target}")


def run_network_delay(conn, target, delay_ms=200, duration_seconds=60):
    """Inject network latency into a container using Pumba."""
    print(f"[NETWORK DELAY] Starting on {target}: {delay_ms}ms delay for {duration_seconds}s")
    row_id = log_experiment_start(
        conn, "network_delay", target,
        parameters={"delay_ms": delay_ms, "duration_seconds": duration_seconds},
        notes="Pumba netem delay"
    )
    proc = subprocess.Popen(
        [
            "pumba", "netem",
            "--duration", f"{duration_seconds}s",
            "delay",
            "--time", str(delay_ms),
            target,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(duration_seconds + 5)  # extra 5s buffer for Pumba to clean up
    proc.terminate()
    log_experiment_end(conn, row_id)
    print(f"[NETWORK DELAY] Done on {target}")


def run_packet_loss(conn, target, loss_percent=30, duration_seconds=60):
    """Inject packet loss into a container using Pumba."""
    print(f"[PACKET LOSS] Starting on {target}: {loss_percent}% loss for {duration_seconds}s")
    row_id = log_experiment_start(
        conn, "packet_loss", target,
        parameters={"loss_percent": loss_percent, "duration_seconds": duration_seconds},
        notes="Pumba netem loss"
    )
    proc = subprocess.Popen(
        [
            "pumba", "netem",
            "--duration", f"{duration_seconds}s",
            "loss",
            "--percent", str(loss_percent),
            target,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(duration_seconds + 5)
    proc.terminate()
    log_experiment_end(conn, row_id)
    print(f"[PACKET LOSS] Done on {target}")


def run_container_kill(conn, target):
    """Kill and restart a container, simulating a crash."""
    print(f"[CONTAINER KILL] Killing {target}")
    row_id = log_experiment_start(
        conn, "container_kill", target,
        notes="docker compose restart"
    )
    service_name = target.replace("sentinel-", "").rsplit("-", 1)[0]
    subprocess.run(["docker", "compose", "restart", service_name], capture_output=True)
    time.sleep(5)
    log_experiment_end(conn, row_id)
    print(f"[CONTAINER KILL] Done — {target} restarted")


if __name__ == "__main__":
    conn = psycopg2.connect(**DB_CONFIG)
    print("Chaos runner ready. Running one experiment of each type as a test...\n")

    target = "sentinel-catalogue-1"

    # Run one of each type as a quick proof-of-concept
    run_container_kill(conn, target)
    time.sleep(30)  # let the system recover between experiments

    run_cpu_stress(conn, target, duration_seconds=60)
    time.sleep(30)

    run_network_delay(conn, target, delay_ms=200, duration_seconds=60)
    time.sleep(30)

    run_packet_loss(conn, target, loss_percent=30, duration_seconds=60)

    conn.close()
    print("\nAll test experiments complete. Check the fault_injections table.")