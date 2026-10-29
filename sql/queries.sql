-- =====================================================================================
-- Analytical (READ) queries.  Loaded by notebooks/01_database_pipeline.ipynb
-- =====================================================================================

-- name: q01_table_row_counts
-- desc: sanity check of every layer
SELECT 'raw_city_day' AS tbl, COUNT(*) AS n FROM raw_city_day
UNION ALL SELECT 'dim_city', COUNT(*) FROM dim_city
UNION ALL SELECT 'fact_aqi', COUNT(*) FROM fact_aqi
UNION ALL SELECT 'festival_calendar', COUNT(*) FROM festival_calendar
UNION ALL SELECT 'audit_log', COUNT(*) FROM audit_log;

-- name: q02_city_coverage
-- desc: how many days / AQI values does each city have, and over which period?
SELECT city, region, n_days, n_days_with_aqi, first_date, last_date,
       ROUND(100.0 * (n_days - n_days_with_aqi) / n_days, 1) AS pct_aqi_missing, mean_aqi, is_suspect
FROM v_city_summary ORDER BY n_days DESC;

-- name: q03_missing_by_column
-- desc: percentage of NULLs per column in the fact table
SELECT ROUND(100.0*SUM(pm25 IS NULL)/COUNT(*),1) AS pm25, ROUND(100.0*SUM(pm10 IS NULL)/COUNT(*),1) AS pm10,
       ROUND(100.0*SUM(no2 IS NULL)/COUNT(*),1) AS no2, ROUND(100.0*SUM(so2 IS NULL)/COUNT(*),1) AS so2,
       ROUND(100.0*SUM(co IS NULL)/COUNT(*),1) AS co, ROUND(100.0*SUM(o3 IS NULL)/COUNT(*),1) AS o3,
       ROUND(100.0*SUM(nh3 IS NULL)/COUNT(*),1) AS nh3, ROUND(100.0*SUM(benzene IS NULL)/COUNT(*),1) AS benzene,
       ROUND(100.0*SUM(xylene IS NULL)/COUNT(*),1) AS xylene, ROUND(100.0*SUM(aqi IS NULL)/COUNT(*),1) AS aqi
FROM fact_aqi;

-- name: q04_worst_days_delhi
-- desc: the 10 most polluted days recorded in Delhi
SELECT date, aqi, aqi_bucket, pm25, pm10 FROM v_aqi_full
WHERE city = 'Delhi' AND aqi IS NOT NULL ORDER BY aqi DESC LIMIT 10;

-- name: q05_monthly_mean_core_cities
-- desc: month-of-year profile (all years pooled) for Delhi, Chandigarh and Mumbai
SELECT city, CAST(strftime('%m', date) AS INTEGER) AS month, ROUND(AVG(aqi), 1) AS mean_aqi, COUNT(aqi) AS n
FROM v_aqi_full WHERE city IN ('Delhi','Chandigarh','Mumbai')
GROUP BY city, month ORDER BY city, month;

-- name: q06_severe_days_per_city_year
-- desc: number of 'Severe' days per city and year (top rows)
SELECT city, strftime('%Y', date) AS year, SUM(aqi_bucket = 'Severe') AS severe_days, COUNT(aqi) AS days_with_aqi
FROM v_aqi_full GROUP BY city, year HAVING severe_days > 0 ORDER BY severe_days DESC LIMIT 15;

-- name: q07_rolling_7day_delhi
-- desc: window function - 7-day moving average of Delhi's AQI (Oct-Nov 2019 shown)
SELECT date, aqi,
       ROUND(AVG(aqi) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS aqi_7d_avg
FROM v_aqi_full WHERE city = 'Delhi' AND date BETWEEN '2019-10-15' AND '2019-11-20' ORDER BY date;

-- name: q08_diwali_effect
-- desc: Diwali window (D-1..D+3) vs the quiet week before (D-10..D-4), per city and year
SELECT c.city_name AS city, strftime('%Y', fc.date) AS year,
       ROUND(AVG(CASE WHEN julianday(f.date) BETWEEN julianday(fc.date)-1  AND julianday(fc.date)+3 THEN f.aqi END), 1) AS aqi_diwali_window,
       ROUND(AVG(CASE WHEN julianday(f.date) BETWEEN julianday(fc.date)-10 AND julianday(fc.date)-4 THEN f.aqi END), 1) AS aqi_pre_week
FROM festival_calendar fc
JOIN fact_aqi f  ON julianday(f.date) BETWEEN julianday(fc.date)-10 AND julianday(fc.date)+3
JOIN dim_city c  ON c.city_id = f.city_id
WHERE fc.festival = 'Diwali' AND c.city_name IN ('Delhi','Chandigarh','Mumbai','Amritsar','Gurugram','Lucknow')
GROUP BY c.city_name, fc.date
HAVING aqi_diwali_window IS NOT NULL AND aqi_pre_week IS NOT NULL
ORDER BY c.city_name, year;

-- name: q09_bucket_share_by_city
-- desc: share of days in each AQI category for the comparison cities
SELECT city,
       ROUND(100.0*SUM(aqi_bucket='Good')/COUNT(aqi),1)         AS good,
       ROUND(100.0*SUM(aqi_bucket='Satisfactory')/COUNT(aqi),1) AS satisfactory,
       ROUND(100.0*SUM(aqi_bucket='Moderate')/COUNT(aqi),1)     AS moderate,
       ROUND(100.0*SUM(aqi_bucket='Poor')/COUNT(aqi),1)         AS poor,
       ROUND(100.0*SUM(aqi_bucket='Very Poor')/COUNT(aqi),1)    AS very_poor,
       ROUND(100.0*SUM(aqi_bucket='Severe')/COUNT(aqi),1)       AS severe
FROM v_aqi_full WHERE city IN ('Delhi','Chandigarh','Mumbai','Amritsar','Gurugram','Lucknow','Jaipur','Bengaluru')
GROUP BY city ORDER BY severe DESC;

-- name: q10_weekday_effect
-- desc: average AQI by day of week (0 = Sunday) over the cities with full history
SELECT CAST(strftime('%w', date) AS INTEGER) AS weekday_sun0, ROUND(AVG(aqi), 1) AS mean_aqi, COUNT(aqi) AS n
FROM v_aqi_full WHERE is_suspect = 0 GROUP BY weekday_sun0 ORDER BY weekday_sun0;

-- name: q11_lockdown_vs_2019
-- desc: mean AQI during 25 Mar - 31 May in 2019 vs 2020 (COVID-19 lockdown natural experiment)
SELECT city,
       ROUND(AVG(CASE WHEN date BETWEEN '2019-03-25' AND '2019-05-31' THEN aqi END), 1) AS aqi_2019,
       ROUND(AVG(CASE WHEN date BETWEEN '2020-03-25' AND '2020-05-31' THEN aqi END), 1) AS aqi_2020,
       ROUND(100.0 * (AVG(CASE WHEN date BETWEEN '2020-03-25' AND '2020-05-31' THEN aqi END)
                    / AVG(CASE WHEN date BETWEEN '2019-03-25' AND '2019-05-31' THEN aqi END) - 1), 1) AS pct_change
FROM v_aqi_full WHERE is_suspect = 0
GROUP BY city HAVING aqi_2019 IS NOT NULL AND aqi_2020 IS NOT NULL ORDER BY pct_change;

-- name: q12_region_summary
-- desc: JOIN + GROUP BY across the dimension - average AQI and pollutant levels per region
SELECT region, COUNT(DISTINCT city) AS n_cities, ROUND(AVG(aqi),1) AS mean_aqi,
       ROUND(AVG(pm25),1) AS pm25, ROUND(AVG(pm10),1) AS pm10, ROUND(AVG(no2),1) AS no2, ROUND(AVG(so2),1) AS so2
FROM v_aqi_full WHERE is_suspect = 0 GROUP BY region ORDER BY mean_aqi DESC;

-- name: q13_data_quality_no_equals_co
-- desc: evidence behind the 'suspect city' flag - share of days with NO == CO
SELECT city, ROUND(100.0 * AVG(CASE WHEN no_ IS NOT NULL AND co IS NOT NULL AND no_ = co THEN 1.0 ELSE 0.0 END), 1) AS pct_days_no_equals_co,
       SUM(is_outlier) AS outlier_rows
FROM v_aqi_full GROUP BY city ORDER BY pct_days_no_equals_co DESC LIMIT 6;

-- name: q14_audit_log
-- desc: what the cleaning pipeline did (the database's own change history)
SELECT step, table_name, rows_affected, description FROM audit_log ORDER BY log_id;
