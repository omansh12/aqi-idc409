"""End-to-end database build (raw CSV -> cleaned star schema).  Used by run_pipeline.py and notebook 01."""
from . import db
from .config import DATA_RAW, DB_PATH, SQL_DIR


def build_database(csv_path=DATA_RAW, db_path=DB_PATH, verbose=True):
    if db_path.exists():
        db_path.unlink()
    conn = db.get_conn(db_path)
    db.run_script(conn, SQL_DIR / "schema.sql")
    n = db.load_raw_csv(conn, csv_path)
    if verbose:
        print(f"Loaded {n:,} raw rows")
    steps = db.load_named_sql(SQL_DIR / "clean_pipeline.sql")
    # steps up to load_dim_city, then metadata, then the rest
    first = ["trim_city_names", "unify_city_aliases", "delete_duplicate_rows", "delete_empty_rows", "load_dim_city"]
    db.run_steps(conn, steps, only=first, verbose=verbose)
    db.populate_city_metadata(conn)
    db.populate_festivals(conn)
    rest = [s for s in steps if s not in first]
    log = db.run_steps(conn, steps, only=rest, verbose=verbose)
    return conn, log


def make_feature_table(conn):
    """Read the cleaned fact table from SQLite and build the full modelling table (same logic as notebook 02)."""
    from . import features, cpcb
    fact = db.read_fact(conn)
    work = features.build_feature_table(fact)
    work["aqi_cpcb"], work["dominant"] = cpcb.reconstruct_aqi(work)
    work["in_model_pop"] = ((work["valid_same_day"] == 1) & (work["is_suspect"] == 0)).astype(int)
    return work
