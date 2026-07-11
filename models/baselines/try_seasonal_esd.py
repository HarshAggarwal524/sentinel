import pandas as pd
from seasonal_esd import detect_anomalies_seasonal_esd

df = pd.read_csv("../experiments/NAB/data/artificialWithAnomaly/art_daily_jumpsup.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

anomalies = detect_anomalies_seasonal_esd(df, period=288, threshold=3.0)
print(f"Total points: {len(df)}")
print(f"Flagged as anomalous: {anomalies.sum()}")
print(df[anomalies][["timestamp", "value"]].head(10))