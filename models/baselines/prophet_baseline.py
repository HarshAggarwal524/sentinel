import pandas as pd
from prophet import Prophet


def detect_anomalies_prophet(df: pd.DataFrame, interval_width: float = 0.99) -> pd.Series:
    """
    df: DataFrame with columns ['timestamp', 'value'].
    interval_width: how wide Prophet's confidence range should be
                     (0.99 = predict a range covering 99% of expected outcomes;
                      anything outside this is unusual enough to flag).

    Returns a boolean Series (True = anomalous), same length as df.
    """
    prophet_df = df.rename(columns={"timestamp": "ds", "value": "y"})

    model = Prophet(interval_width=interval_width)
    model.fit(prophet_df)

    forecast = model.predict(prophet_df[["ds"]])

    is_anomaly = (
        (prophet_df["y"] < forecast["yhat_lower"]) |
        (prophet_df["y"] > forecast["yhat_upper"])
    )

    return is_anomaly.values