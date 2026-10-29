"""Unit tests - run with:  python -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config, cpcb, db, features, modeling          # noqa: E402
from src.pipeline import build_database, make_feature_table    # noqa: E402


class TestBuckets(unittest.TestCase):
    def test_band_edges(self):
        cases = {0: "Good", 50: "Good", 51: "Satisfactory", 100: "Satisfactory", 101: "Moderate", 200: "Moderate",
                 201: "Poor", 300: "Poor", 301: "Very Poor", 400: "Very Poor", 401: "Severe", 900: "Severe"}
        for aqi, name in cases.items():
            self.assertEqual(config.aqi_to_bucket(aqi), name, aqi)
        self.assertIsNone(config.aqi_to_bucket(float("nan")))


class TestCPCB(unittest.TestCase):
    def test_breakpoints(self):
        df = pd.DataFrame({"pm25": [30, 60, 120], "pm10": [50, 100, 350], "no2": [40, 80, 280], "o3": [np.nan] * 3,
                           "co": [np.nan] * 3, "so2": [np.nan] * 3, "nh3": [np.nan] * 3})
        aqi, dom = cpcb.reconstruct_aqi(df)
        self.assertEqual(list(aqi.round()), [50, 100, 300])

    def test_completeness_rule(self):
        only_two = pd.DataFrame({"pm25": [100.0], "pm10": [np.nan], "no2": [50.0], "o3": [np.nan], "co": [np.nan], "so2": [np.nan], "nh3": [np.nan]})
        no_pm = pd.DataFrame({"pm25": [np.nan], "pm10": [np.nan], "no2": [50.0], "o3": [30.0], "co": [1.0], "so2": [np.nan], "nh3": [np.nan]})
        self.assertTrue(np.isnan(cpcb.reconstruct_aqi(only_two)[0].iloc[0]))   # < 3 pollutants
        self.assertTrue(np.isnan(cpcb.reconstruct_aqi(no_pm)[0].iloc[0]))      # no PM value


class TestFeatures(unittest.TestCase):
    def test_event_windows(self):
        d = pd.DataFrame({"date": pd.to_datetime(["2019-10-25", "2019-10-26", "2019-10-30", "2019-10-31", "2020-03-24", "2020-03-25", "2020-05-31", "2020-06-01"])})
        d = features.add_event_features(features.add_calendar_features(d))
        self.assertEqual(d.is_diwali_window.tolist(), [0, 1, 1, 0, 0, 0, 0, 0])      # Diwali 27 Oct 2019: D-1 .. D+3
        self.assertEqual(d.is_lockdown.tolist(), [0, 0, 0, 0, 0, 1, 1, 0])
        self.assertEqual(d.is_stubble_season.tolist()[:4], [1, 1, 1, 1])

    def test_lags_use_calendar_days_not_row_positions(self):
        # a city with a missing day (Jan 3): lag1 of Jan 4 must be NaN, not Jan 2's value
        fact = pd.DataFrame({"city": "X", "city_id": 1, "state": "S", "region": "R", "is_suspect": 0, "is_outlier": 0,
                             "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-04", "2020-01-05"]),
                             "aqi": [10.0, 20.0, 40.0, 50.0], "aqi_bucket": "Good"})
        for c in config.POLLUTANTS: fact[c] = 1.0
        out = features.build_feature_table(fact).set_index("date")
        self.assertTrue(np.isnan(out.loc["2020-01-04", "aqi_lag1"]))
        self.assertEqual(out.loc["2020-01-05", "aqi_lag1"], 40.0)
        self.assertTrue(np.isnan(out.loc["2020-01-02", "aqi_next"]))                  # Jan 3 does not exist
        self.assertEqual(out.loc["2020-01-04", "aqi_next"], 50.0)

    def test_time_split_has_no_overlap(self):
        d = pd.DataFrame({"date": pd.date_range("2018-12-25", periods=20)})
        tr, te = modeling.time_split(d, "2019-01-01")
        self.assertLess(tr.date.max(), te.date.min())
        self.assertEqual(len(tr) + len(te), len(d))


class TestDatabasePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.conn, cls.log = build_database(config.DATA_RAW, Path(cls.tmp.name) / "t.db", verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close(); cls.tmp.cleanup()

    def test_row_counts(self):
        n = lambda t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        self.assertEqual(n("raw_city_day"), 28157)         # 29,531 minus 1,374 completely empty rows
        self.assertEqual(n("fact_aqi"), 28157)
        self.assertEqual(n("dim_city"), 26)

    def test_integrity(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM fact_aqi GROUP BY city_id, date HAVING COUNT(*)>1)").fetchone()[0], 0)

    def test_suspect_city_flagged(self):
        flagged = [r[0] for r in self.conn.execute("SELECT DISTINCT city_name FROM fact_aqi JOIN dim_city USING(city_id) WHERE is_suspect = 1")]
        self.assertEqual(flagged, ["Ahmedabad"])

    def test_placeholder_zeros_removed(self):
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM fact_aqi WHERE co = 0 OR nox = 0 OR benzene = 0 OR toluene = 0 OR xylene = 0").fetchone()[0], 0)

    def test_audit_log_written(self):
        steps = [r[0] for r in self.conn.execute("SELECT step FROM audit_log")]
        for s in ["delete_empty_rows", "load_fact_aqi", "zeros_to_null", "flag_suspect_cities"]:
            self.assertIn(s, steps)

    def test_all_named_queries_run(self):
        for name, q in db.load_named_sql(config.SQL_DIR / "queries.sql").items():
            self.assertIsInstance(db.query(q["sql"], self.conn), pd.DataFrame, name)

    def test_feature_table(self):
        f = make_feature_table(self.conn)
        self.assertEqual(len(f), 28157)
        self.assertEqual(int(f.in_model_pop.sum()), 23500)
        self.assertFalse(f[f.is_suspect == 1].in_model_pop.any())
        # next-day target must be tomorrow's AQI of the same city
        d = f[f.city == "Delhi"].set_index("date")
        self.assertTrue((d["aqi_next"].dropna() == d["aqi"].shift(-1).dropna()).all())


if __name__ == "__main__":
    unittest.main()
