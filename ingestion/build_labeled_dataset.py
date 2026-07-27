import json
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import timezone

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="sentinel",
    user="postgres",
    password="sentinel_dev_pw",
)

CONTEXT_MINUTES_BEFORE = 10
CONTEXT_MINUTES_AFTER = 10
TARGET_METRIC = "container_cpu_usage_seconds_total"

# Direct mapping from container name → Docker ID
CONTAINER_ID_MAP = {
    "sentinel-catalogue-1": "1d894f748d7a4951c1b7fedebe9dad250f960b5eb0209d9bb7fdf0ba4deace00",
    "sentinel-carts-1":     "2b22ca3cac63908ee1083a91b4872713663357c9f123fba32b206f9316e215ca",
    "sentinel-orders-1":    "acd33dd0fe92dd0ce2250fdffce6a53cf571a177e5f77eda9d80991239a51625",
    "sentinel-front-end-1": "559ab44c1d30c4c84755cb776b9e47deb9646423d228cb149207541590415c16",
    "sentinel-payment-1":   "1f19b691f0bc4628049a0c5cfccf92e0ca85a47338c45579b9dd50b27c1daad2",
    "sentinel-shipping-1":  "a4a494813b85655ed18568bdffaf49f525dd6827619fb8227aa5d8f5aff98ed1",
}


def build_labeled_dataset():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, experiment_type, target_container, start_time, end_time
        FROM fault_injections
        WHERE end_time IS NOT NULL
        ORDER BY start_time;
    """)
    faults = cur.fetchall()
    print(f"Found {len(faults)} fault injections to process.")

    all_windows = {}
    dataset_rows = []
    skipped = 0

    for fault in faults:
        fault_id = fault["id"]
        experiment_type = fault["experiment_type"]
        target = fault["target_container"]
        fault_start = fault["start_time"]
        fault_end = fault["end_time"]

        container_id = CONTAINER_ID_MAP.get(target)
        if not container_id:
            print(f"  [skip] Fault {fault_id}: no ID mapping for {target}")
            skipped += 1
            continue

        docker_id_label = f"/docker/{container_id}"

        cur.execute("""
            SELECT time, value
            FROM metrics
            WHERE metric_name = %s
              AND labels->>'id' = %s
              AND time >= %s - INTERVAL '10 minutes'
              AND time <= %s + INTERVAL '10 minutes'
            ORDER BY time ASC;
        """, (TARGET_METRIC, docker_id_label, fault_start, fault_end))
        rows = cur.fetchall()

        if len(rows) < 5:
            print(f"  [skip] Fault {fault_id} ({experiment_type} on {target}): "
                  f"only {len(rows)} metric rows — insufficient data")
            skipped += 1
            continue

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["time"], utc=True)
        df = df[["timestamp", "value"]].drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)

        label_window = [
            fault_start.strftime("%Y-%m-%d %H:%M:%S.%f"),
            fault_end.strftime("%Y-%m-%d %H:%M:%S.%f"),
        ]

        key = f"sock_shop/{experiment_type}/{target}/fault_{fault_id}.csv"
        all_windows[key] = [label_window]
        dataset_rows.append({
            "key": key,
            "df": df,
            "fault_id": fault_id,
            "experiment_type": experiment_type,
            "target": target,
        })

        print(f"  [ok] Fault {fault_id}: {experiment_type} on {target} — {len(df)} metric points")

    cur.close()
    conn.close()

    print(f"\nBuilt {len(dataset_rows)} usable labeled windows "
          f"(skipped {skipped} due to insufficient metrics or missing ID mapping).")
    return dataset_rows, all_windows


if __name__ == "__main__":
    import os
    os.makedirs("sock_shop_dataset", exist_ok=True)

    dataset_rows, all_windows = build_labeled_dataset()

    for entry in dataset_rows:
        key = entry["key"]
        df = entry["df"]
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        os.makedirs(f"sock_shop_dataset/{'/'.join(key.split('/')[:-1])}", exist_ok=True)
        df.to_csv(f"sock_shop_dataset/{key}", index=False)

    with open("sock_shop_dataset/labels.json", "w") as f:
        json.dump(all_windows, f, indent=2)

    print(f"Saved {len(dataset_rows)} CSV files + labels.json to sock_shop_dataset/")