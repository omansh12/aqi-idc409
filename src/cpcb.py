"""CPCB (India) AQI sub-index calculator, used to (a) validate the reported AQI and (b) find the dominant pollutant.

AQI = max(sub-indices) and needs >= 3 pollutants of which at least one is PM2.5 or PM10.
Breakpoints are the CPCB 24-h values (CO in mg/m3).  The top band is extrapolated linearly,
so values above 500 are possible (the dataset's own AQI also goes beyond 500).
"""
import numpy as np
import pandas as pd

# concentration breakpoints -> index breakpoints  (0,50,100,200,300,400,500)
_INDEX = [0, 50, 100, 200, 300, 400, 500]
_BREAKS = {
    "pm25": [0, 30, 60, 90, 120, 250, 380],
    "pm10": [0, 50, 100, 250, 350, 430, 510],
    "no2":  [0, 40, 80, 180, 280, 400, 480],
    "o3":   [0, 50, 100, 168, 208, 748, 1000],
    "co":   [0, 1, 2, 10, 17, 34, 50],
    "so2":  [0, 40, 80, 380, 800, 1600, 2400],
    "nh3":  [0, 200, 400, 800, 1200, 1800, 2400],
}
SUBINDEX_POLLUTANTS = list(_BREAKS)


def _interp(conc, breaks):
    conc = np.asarray(conc, dtype=float)
    out = np.interp(conc, breaks, _INDEX)
    slope = (_INDEX[-1] - _INDEX[-2]) / (breaks[-1] - breaks[-2])
    out = np.where(conc > breaks[-1], _INDEX[-1] + (conc - breaks[-1]) * slope, out)
    return np.where(np.isnan(conc), np.nan, out)


def subindices(df):
    """Return a DataFrame with one sub-index column per pollutant (named si_<pollutant>)."""
    return pd.DataFrame({f"si_{p}": _interp(df[p].values, b) for p, b in _BREAKS.items()}, index=df.index)


def reconstruct_aqi(df):
    """Return (aqi_cpcb, dominant_pollutant) following the CPCB completeness rule."""
    si = subindices(df)
    n_ok = si.notna().sum(axis=1)
    has_pm = si[["si_pm25", "si_pm10"]].notna().any(axis=1)
    ok = (n_ok >= 3) & has_pm
    aqi = si.max(axis=1).where(ok)
    dom = si.fillna(-1).idxmax(axis=1).where(ok).str.replace("si_", "", regex=False)
    return aqi, dom
