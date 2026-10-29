"""Feature engineering: calendar, festival / event flags, lag features and the modelling table."""
import numpy as np
import pandas as pd

from .config import (FESTIVALS, FESTIVAL_WINDOWS, STUBBLE_START, STUBBLE_END, LOCKDOWN_START, LOCKDOWN_END,
                     SEASONS, POLLUTANTS, MODEL_POLLUTANTS, aqi_to_bucket)


# ----------------------------------------------------------------------------- calendar
def add_calendar_features(df):
    d = df["date"]
    df["year"] = d.dt.year
    df["month"] = d.dt.month
    df["day"] = d.dt.day
    df["dayofweek"] = d.dt.dayofweek               # 0 = Monday
    df["dayofyear"] = d.dt.dayofyear
    df["quarter"] = d.dt.quarter
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["season"] = df["month"].map(SEASONS)
    df["is_winter"] = (df["season"] == "Winter").astype(int)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)   # cyclic encoding: December is next to January
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


# ----------------------------------------------------------------------------- festivals & events
def days_to_nearest(dates, festival_dates):
    """Signed days from each date to the nearest festival date (negative = before the festival)."""
    fd = pd.to_datetime(pd.Series(festival_dates)).values.astype("datetime64[D]")
    dd = dates.values.astype("datetime64[D]")
    diff = (dd[:, None] - fd[None, :]).astype(int)           # date - festival
    idx = np.abs(diff).argmin(axis=1)
    return diff[np.arange(len(dd)), idx]


def add_event_features(df):
    for fest, dates in FESTIVALS.items():
        before, after = FESTIVAL_WINDOWS[fest]
        rel = days_to_nearest(df["date"], dates)
        df[f"days_from_{fest.lower()}"] = rel                # signed distance, used for event-study plots
        df[f"is_{fest.lower()}_window"] = ((rel >= -before) & (rel <= after)).astype(int)
    md = df["date"].dt.month * 100 + df["date"].dt.day
    s, e = STUBBLE_START[0] * 100 + STUBBLE_START[1], STUBBLE_END[0] * 100 + STUBBLE_END[1]
    df["is_stubble_season"] = ((md >= s) & (md <= e)).astype(int)
    df["is_lockdown"] = ((df["date"] >= LOCKDOWN_START) & (df["date"] <= LOCKDOWN_END)).astype(int)
    return df


# ----------------------------------------------------------------------------- lags (for next-day forecasting)
def add_lag_features(df):
    """Lags / rolling stats per city (data must be sorted by city, date and contiguous per city)."""
    g = df.groupby("city", sort=False)
    # guard: lags are only valid when every city has consecutive daily dates
    gaps = g["date"].diff().dt.days.dropna()
    assert (gaps == 1).all(), "dates are not contiguous within a city - reindex before adding lags"
    for k in (1, 2, 3, 7):
        df[f"aqi_lag{k}"] = g["aqi"].shift(k)
    df["aqi_roll3"] = g["aqi"].transform(lambda s: s.rolling(3, min_periods=2).mean())
    df["aqi_roll7"] = g["aqi"].transform(lambda s: s.rolling(7, min_periods=3).mean())
    df["aqi_roll7_std"] = g["aqi"].transform(lambda s: s.rolling(7, min_periods=3).std())
    df["pm25_lag1"] = g["pm25"].shift(1)
    df["pm10_lag1"] = g["pm10"].shift(1)
    df["aqi_change_1d"] = df["aqi"] - df["aqi_lag1"]
    df["aqi_next"] = g["aqi"].shift(-1)                       # TARGET of the next-day task
    df["bucket_next"] = df["aqi_next"].map(aqi_to_bucket)
    return df


# ----------------------------------------------------------------------------- feature lists
LAG_FEATURES = ["aqi", "aqi_lag1", "aqi_lag2", "aqi_lag3", "aqi_lag7", "aqi_roll3", "aqi_roll7",
                "aqi_roll7_std", "pm25_lag1", "pm10_lag1", "aqi_change_1d"]
CALENDAR_FEATURES = ["month_sin", "month_cos", "dayofweek", "is_weekend", "is_winter"]
EVENT_FEATURES = ["is_diwali_window", "is_holi_window", "is_dussehra_window", "is_stubble_season", "is_lockdown"]
CATEGORICAL_FEATURES = ["city", "season"]
ALL_SAME_DAY_FEATURES = MODEL_POLLUTANTS + CALENDAR_FEATURES + EVENT_FEATURES + CATEGORICAL_FEATURES


# ----------------------------------------------------------------------------- the modelling table
def densify(df):
    """Re-insert the days that were removed as 'empty' so every city has a gap-free daily calendar.
    Lags / shifts are only correct on a contiguous calendar.  Re-inserted rows get has_record = 0."""
    parts = []
    for city, g in df.groupby("city", sort=True):
        idx = pd.date_range(g["date"].min(), g["date"].max(), freq="D", name="date")
        g2 = g.set_index("date").reindex(idx)
        for c in ("city", "city_id", "state", "region", "is_suspect"):
            g2[c] = g[c].iloc[0]
        g2["is_outlier"] = g2["is_outlier"].fillna(0).astype(int)
        g2["has_record"] = g2.index.isin(g["date"]).astype(int)
        parts.append(g2.reset_index())
    return pd.concat(parts, ignore_index=True)


def build_feature_table(fact, ffill_limit=3):
    """From the cleaned fact table (read from SQLite) to the full feature table.

    * short gaps (<= `ffill_limit` days) in pollutant columns are filled with the last observation of the
      same city (causal: never uses the future).  AQI itself is never imputed.
    * the calendar is first made gap-free per city (needed for correct lags)
    * valid_same_day : AQI known, at least one PM value, >= 3 pollutant values (the CPCB completeness rule)
    * valid_next_day : valid_same_day and tomorrow's AQI is known
    """
    df = densify(fact.sort_values(["city", "date"]).reset_index(drop=True))
    before = df[POLLUTANTS].isna()
    df[POLLUTANTS] = df.groupby("city")[POLLUTANTS].ffill(limit=ffill_limit)
    df["n_ffilled"] = (before & df[POLLUTANTS].notna()).sum(axis=1)
    df = add_calendar_features(df)
    df = add_event_features(df)
    df = add_lag_features(df)
    n_pol = df[MODEL_POLLUTANTS].notna().sum(axis=1)
    has_pm = df[["pm25", "pm10"]].notna().any(axis=1)
    df["valid_same_day"] = (df["aqi"].notna() & has_pm & (n_pol >= 3)).astype(int)
    df["valid_next_day"] = (df["valid_same_day"].astype(bool) & df["aqi_next"].notna()).astype(int)
    df = df[df["has_record"] == 1].drop(columns="has_record").reset_index(drop=True)   # drop the placeholder rows again
    return df
