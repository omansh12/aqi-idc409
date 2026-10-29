-- =====================================================================================
-- AQI project - database schema (SQLite)
-- Star-like design:  dim_city  <-  fact_aqi  (+ festival_calendar, audit_log, model_results)
-- =====================================================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_aqi_full;
DROP VIEW  IF EXISTS v_city_summary;
DROP TABLE IF EXISTS model_results;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS festival_calendar;
DROP TABLE IF EXISTS aqi_features;
DROP TABLE IF EXISTS fact_aqi;
DROP TABLE IF EXISTS dim_city;
DROP TABLE IF EXISTS raw_city_day;

-- 1) RAW layer: exactly what the CSV contained (only column names normalised)
CREATE TABLE raw_city_day (
    city TEXT, date TEXT,
    pm25 REAL, pm10 REAL, no_ REAL, no2 REAL, nox REAL, nh3 REAL, co REAL, so2 REAL,
    o3 REAL, benzene REAL, toluene REAL, xylene REAL, aqi REAL, aqi_bucket TEXT
);

-- 2) DIMENSION: one row per city
CREATE TABLE dim_city (
    city_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL UNIQUE,
    state     TEXT,
    region    TEXT
);

-- 3) FACT: one row per (city, day) after SQL cleaning
CREATE TABLE fact_aqi (
    city_id INTEGER NOT NULL REFERENCES dim_city(city_id),
    date    TEXT    NOT NULL,                       -- ISO yyyy-mm-dd
    pm25 REAL, pm10 REAL, no_ REAL, no2 REAL, nox REAL, nh3 REAL, co REAL, so2 REAL,
    o3 REAL, benzene REAL, toluene REAL, xylene REAL,
    aqi REAL, aqi_bucket TEXT,
    is_outlier INTEGER NOT NULL DEFAULT 0,          -- 1 = physically extreme / above-scale reading
    is_suspect INTEGER NOT NULL DEFAULT 0,          -- 1 = city flagged for data-quality problems
    PRIMARY KEY (city_id, date)
);
CREATE INDEX idx_fact_date ON fact_aqi(date);

-- 4) Lookup of festival dates (used in SQL analysis of festival effects)
CREATE TABLE festival_calendar (festival TEXT NOT NULL, date TEXT NOT NULL, PRIMARY KEY (festival, date));

-- 5) Governance tables
CREATE TABLE audit_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT DEFAULT CURRENT_TIMESTAMP,
    step          TEXT,
    table_name    TEXT,
    rows_affected INTEGER,
    description   TEXT
);

CREATE TABLE model_results (
    result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT DEFAULT CURRENT_TIMESTAMP,
    task        TEXT,      -- e.g. regression_same_day, classification_next_day
    model       TEXT,
    feature_set TEXT,
    eval_set    TEXT,      -- train / test / test_pre_lockdown / city name ...
    metric      TEXT,
    value       REAL
);

-- 6) Convenience views
CREATE VIEW v_aqi_full AS
SELECT c.city_name AS city, c.state, c.region, f.*
FROM fact_aqi f JOIN dim_city c USING (city_id);

CREATE VIEW v_city_summary AS
SELECT c.city_name AS city, c.region,
       COUNT(*)                        AS n_days,
       MIN(f.date)                     AS first_date,
       MAX(f.date)                     AS last_date,
       COUNT(f.aqi)                    AS n_days_with_aqi,
       ROUND(AVG(f.aqi), 1)            AS mean_aqi,
       MAX(f.is_suspect)               AS is_suspect
FROM fact_aqi f JOIN dim_city c USING (city_id)
GROUP BY c.city_id;
