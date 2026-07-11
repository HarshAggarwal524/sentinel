import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


def detect_anomalies_seasonal_esd(df: pd.DataFrame, period: int = 288, threshold: float = 3.0) -> pd.Series:
    """
    df: DataFrame with columns ['timestamp', 'value'], timestamp as datetime.
    period: expected seasonal cycle length, in number of data points
            (NAB data is usually 5-minute intervals, so 288 = one full day).
    threshold: how many standard deviations away from zero counts as anomalous.

    Returns a boolean Series (True = anomalous), same length as df.
    """
    series = df.set_index("timestamp")["value"]

    # Decompose into trend + seasonal + residual (leftover) components
    stl_result = STL(series, period=period, robust=True).fit()
    residual = stl_result.resid

    # Anomalies = residual points that are unusually far from zero,
    # measured in standard deviations (this is the "ESD" part - Extreme Studentized Deviate)
    residual_std = residual.std()
    is_anomaly = (residual.abs() > threshold * residual_std)

    return is_anomaly.reindex(df["timestamp"]).values