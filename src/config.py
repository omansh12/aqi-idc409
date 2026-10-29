"""Central configuration: paths, constants, domain knowledge (AQI bands, festivals, regions)."""
from pathlib import Path

# ----------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw" / "city_day.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "db" / "aqi.db"
SQL_DIR = ROOT / "sql"
FIG_DIR = ROOT / "reports" / "figures"
RESULTS_DIR = ROOT / "results"
MODELS_DIR = ROOT / "models"

RANDOM_STATE = 42

# ----------------------------------------------------------------------------- columns
# CSV header -> database / pandas column name ("NO" is an SQL keyword, so it becomes no_)
COLUMN_MAP = {
    "City": "city", "Date": "date", "PM2.5": "pm25", "PM10": "pm10", "NO": "no_",
    "NO2": "no2", "NOx": "nox", "NH3": "nh3", "CO": "co", "SO2": "so2", "O3": "o3",
    "Benzene": "benzene", "Toluene": "toluene", "Xylene": "xylene",
    "AQI": "aqi", "AQI_Bucket": "aqi_bucket",
}
POLLUTANTS = ["pm25", "pm10", "no_", "no2", "nox", "nh3", "co", "so2", "o3",
              "benzene", "toluene", "xylene"]
# Xylene is 61 % missing -> excluded from modelling (kept in the database).
MODEL_POLLUTANTS = [p for p in POLLUTANTS if p != "xylene"]
LABELS = {"pm25": "PM2.5", "pm10": "PM10", "no_": "NO", "no2": "NO2", "nox": "NOx",
          "nh3": "NH3", "co": "CO", "so2": "SO2", "o3": "O3", "benzene": "Benzene",
          "toluene": "Toluene", "xylene": "Xylene", "aqi": "AQI"}

# ----------------------------------------------------------------------------- AQI categories (CPCB, India)
BUCKET_ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
BUCKET_BOUNDS = [50, 100, 200, 300, 400]            # upper bounds of the first five bands
BUCKET_COLORS = {"Good": "#2e9e4f", "Satisfactory": "#9ccc3c", "Moderate": "#f2c500",
                 "Poor": "#f28c00", "Very Poor": "#d62728", "Severe": "#7b1113"}


def aqi_to_bucket(aqi):
    """Map a numeric AQI to its CPCB category (returns None for NaN)."""
    if aqi is None or aqi != aqi:
        return None
    for bound, name in zip(BUCKET_BOUNDS, BUCKET_ORDER):
        if aqi <= bound:
            return name
    return "Severe"


# ----------------------------------------------------------------------------- geography
STATE = {
    "Ahmedabad": "Gujarat", "Aizawl": "Mizoram", "Amaravati": "Andhra Pradesh",
    "Amritsar": "Punjab", "Bengaluru": "Karnataka", "Bhopal": "Madhya Pradesh",
    "Brajrajnagar": "Odisha", "Chandigarh": "Chandigarh (UT)", "Chennai": "Tamil Nadu",
    "Coimbatore": "Tamil Nadu", "Delhi": "Delhi (UT)", "Ernakulam": "Kerala",
    "Gurugram": "Haryana", "Guwahati": "Assam", "Hyderabad": "Telangana",
    "Jaipur": "Rajasthan", "Jorapokhar": "Jharkhand", "Kochi": "Kerala",
    "Kolkata": "West Bengal", "Lucknow": "Uttar Pradesh", "Mumbai": "Maharashtra",
    "Patna": "Bihar", "Shillong": "Meghalaya", "Talcher": "Odisha",
    "Thiruvananthapuram": "Kerala", "Visakhapatnam": "Andhra Pradesh",
}
REGION = {
    "Amritsar": "North", "Chandigarh": "North", "Delhi": "North", "Gurugram": "North",
    "Jaipur": "North", "Lucknow": "North",
    "Kolkata": "East", "Patna": "East", "Jorapokhar": "East", "Brajrajnagar": "East", "Talcher": "East",
    "Aizawl": "Northeast", "Guwahati": "Northeast", "Shillong": "Northeast",
    "Ahmedabad": "West", "Mumbai": "West", "Bhopal": "Central",
    "Amaravati": "South", "Bengaluru": "South", "Chennai": "South", "Coimbatore": "South",
    "Ernakulam": "South", "Hyderabad": "South", "Kochi": "South",
    "Thiruvananthapuram": "South", "Visakhapatnam": "South",
}

# Cities used for the head-to-head comparison. The brief names Delhi, Chandigarh and Mumbai
# "or nearby cities": Amritsar & Gurugram neighbour Chandigarh/Delhi (same stubble-burning / NCR airshed),
# Lucknow & Jaipur complete the northern belt, Bengaluru is a clean southern reference.
CORE_CITIES = ["Delhi", "Chandigarh", "Mumbai"]
COMPARE_CITIES = ["Delhi", "Chandigarh", "Mumbai", "Amritsar", "Gurugram", "Lucknow", "Jaipur", "Bengaluru"]
NORTH_CITIES = ["Delhi", "Chandigarh", "Amritsar", "Gurugram", "Lucknow", "Jaipur"]

# ----------------------------------------------------------------------------- events
# Main festival dates (Gregorian). Please double-check against an official calendar before submission.
FESTIVALS = {
    "Diwali":   ["2015-11-11", "2016-10-30", "2017-10-19", "2018-11-07", "2019-10-27", "2020-11-14"],
    "Holi":     ["2015-03-06", "2016-03-24", "2017-03-13", "2018-03-02", "2019-03-21", "2020-03-10"],
    "Dussehra": ["2015-10-22", "2016-10-11", "2017-09-30", "2018-10-19", "2019-10-08", "2020-10-25"],
}
# window (days before, days after) around the festival that is flagged
FESTIVAL_WINDOWS = {"Diwali": (1, 3), "Holi": (1, 1), "Dussehra": (1, 1)}
STUBBLE_START = (10, 15)     # (month, day)  paddy-residue burning season, north India
STUBBLE_END = (11, 30)
LOCKDOWN_START, LOCKDOWN_END = "2020-03-25", "2020-05-31"   # India's strict COVID-19 lockdown phases

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Summer", 4: "Summer", 5: "Summer",
           6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon", 10: "Post-monsoon", 11: "Post-monsoon"}

# ----------------------------------------------------------------------------- modelling
TEST_START = "2019-01-01"           # chronological split: train < 2019-01-01 <= test
VALID_START = "2018-01-01"          # inside the training period, used for feature selection
