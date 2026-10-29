"""Headless data pipeline (no notebooks needed):

    raw CSV  ->  SQLite (raw -> cleaned star schema, every step logged)  ->  feature table (SQLite table + CSV)

Usage:   python run_pipeline.py                 # writes db/aqi.db and data/processed/aqi_features.csv
         python run_pipeline.py --db /tmp/x.db --out /tmp/features.csv
Afterwards run notebooks 03-07 (or `jupyter nbconvert --execute`) for EDA, models and evaluation.
"""
import argparse
from pathlib import Path

from src import config, db
from src.pipeline import build_database, make_feature_table


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=config.DATA_RAW, help="raw city_day.csv")
    ap.add_argument("--db", type=Path, default=config.DB_PATH, help="SQLite file to (re)create")
    ap.add_argument("--out", type=Path, default=config.DATA_PROCESSED / "aqi_features.csv", help="feature table CSV")
    args = ap.parse_args()

    print(f"[1/3] building database {args.db} from {args.csv}")
    conn, log = build_database(args.csv, args.db)
    print("[2/3] building feature table")
    feat = make_feature_table(conn)
    out = feat.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_sql("aqi_features", conn, if_exists="replace", index=False)
    conn.commit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[3/3] done: {len(feat):,} rows, {feat.in_model_pop.sum():,} usable for modelling -> {args.out}")
    print(db.query("SELECT city, n_days, first_date, last_date, mean_aqi, is_suspect FROM v_city_summary ORDER BY n_days DESC LIMIT 5", conn))
    conn.close()


if __name__ == "__main__":
    main()
