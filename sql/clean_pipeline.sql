-- =====================================================================================
-- Cleaning pipeline expressed as SQL steps.  Each block is executed (and logged to
-- audit_log) by src/db.py::run_steps.   Format:  -- name: <step>   -- table: <t>   -- desc: <text>
-- =====================================================================================

-- name: trim_city_names
-- table: raw_city_day
-- desc: UPDATE - strip stray whitespace from city names
UPDATE raw_city_day SET city = TRIM(city) WHERE city <> TRIM(city);

-- name: unify_city_aliases
-- table: raw_city_day
-- desc: UPDATE - map historical / alternative spellings to the canonical city name
UPDATE raw_city_day
SET city = CASE city
    WHEN 'Bangalore'  THEN 'Bengaluru'
    WHEN 'Gurgaon'    THEN 'Gurugram'
    WHEN 'Trivandrum' THEN 'Thiruvananthapuram'
    WHEN 'Vizag'      THEN 'Visakhapatnam'
    WHEN 'Cochin'     THEN 'Kochi'
    WHEN 'Bombay'     THEN 'Mumbai'
    WHEN 'Calcutta'   THEN 'Kolkata'
    WHEN 'Madras'     THEN 'Chennai'
    ELSE city END
WHERE city IN ('Bangalore','Gurgaon','Trivandrum','Vizag','Cochin','Bombay','Calcutta','Madras');

-- name: delete_duplicate_rows
-- table: raw_city_day
-- desc: DELETE - keep only the first row for every (city, date) pair
DELETE FROM raw_city_day
WHERE rowid NOT IN (SELECT MIN(rowid) FROM raw_city_day GROUP BY city, date);

-- name: delete_empty_rows
-- table: raw_city_day
-- desc: DELETE - rows where all 12 pollutants AND the AQI are missing carry no information
DELETE FROM raw_city_day
WHERE pm25 IS NULL AND pm10 IS NULL AND no_ IS NULL AND no2 IS NULL AND nox IS NULL
  AND nh3 IS NULL AND co IS NULL AND so2 IS NULL AND o3 IS NULL AND benzene IS NULL
  AND toluene IS NULL AND xylene IS NULL AND aqi IS NULL;

-- name: load_dim_city
-- table: dim_city
-- desc: INSERT - one dimension row per distinct city
INSERT INTO dim_city (city_name) SELECT DISTINCT city FROM raw_city_day ORDER BY city;

-- name: load_fact_aqi
-- table: fact_aqi
-- desc: INSERT ... SELECT - move cleaned raw rows into the fact table with the city surrogate key
INSERT INTO fact_aqi (city_id, date, pm25, pm10, no_, no2, nox, nh3, co, so2, o3,
                      benzene, toluene, xylene, aqi, aqi_bucket)
SELECT c.city_id, r.date, r.pm25, r.pm10, r.no_, r.no2, r.nox, r.nh3, r.co, r.so2, r.o3,
       r.benzene, r.toluene, r.xylene, r.aqi, r.aqi_bucket
FROM raw_city_day r JOIN dim_city c ON c.city_name = r.city;

-- name: zeros_to_null
-- table: fact_aqi
-- desc: UPDATE - exact zeros in CO, NOx, Benzene, Toluene, Xylene are placeholders for "no reading" (see EDA), set to NULL
UPDATE fact_aqi
SET co = NULLIF(co, 0), nox = NULLIF(nox, 0), benzene = NULLIF(benzene, 0),
    toluene = NULLIF(toluene, 0), xylene = NULLIF(xylene, 0)
WHERE co = 0 OR nox = 0 OR benzene = 0 OR toluene = 0 OR xylene = 0;

-- name: fix_aqi_bucket
-- table: fact_aqi
-- desc: UPDATE - make aqi_bucket consistent with the CPCB bands of the numeric AQI
UPDATE fact_aqi
SET aqi_bucket = CASE WHEN aqi <= 50 THEN 'Good' WHEN aqi <= 100 THEN 'Satisfactory'
                      WHEN aqi <= 200 THEN 'Moderate' WHEN aqi <= 300 THEN 'Poor'
                      WHEN aqi <= 400 THEN 'Very Poor' ELSE 'Severe' END
WHERE aqi IS NOT NULL
  AND (aqi_bucket IS NULL OR aqi_bucket <> CASE WHEN aqi <= 50 THEN 'Good' WHEN aqi <= 100 THEN 'Satisfactory'
                      WHEN aqi <= 200 THEN 'Moderate' WHEN aqi <= 300 THEN 'Poor'
                      WHEN aqi <= 400 THEN 'Very Poor' ELSE 'Severe' END);

-- name: flag_outliers
-- table: fact_aqi
-- desc: UPDATE - flag readings above the 0-500 AQI scale or at sensor ceilings (kept, not deleted)
UPDATE fact_aqi SET is_outlier = 1 WHERE aqi > 500 OR pm25 >= 900 OR pm10 >= 1000;

-- name: flag_suspect_cities
-- table: fact_aqi
-- desc: UPDATE - flag cities where NO equals CO on >30% of days (copy-paste data-entry error signature)
UPDATE fact_aqi SET is_suspect = 1
WHERE city_id IN (
    SELECT city_id FROM fact_aqi
    GROUP BY city_id
    HAVING AVG(CASE WHEN no_ IS NOT NULL AND co IS NOT NULL AND no_ = co THEN 1.0 ELSE 0.0 END) > 0.30
);
