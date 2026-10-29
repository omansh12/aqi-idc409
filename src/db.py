"""SQLite helpers: connection, named-SQL loader, logged step runner, results logging."""
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .config import DB_PATH, SQL_DIR, COLUMN_MAP, STATE, REGION, FESTIVALS


def get_conn(path=DB_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection(path=DB_PATH):
    conn = get_conn(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def query(sql, conn=None, params=None):
    """READ: run a SELECT and return a DataFrame."""
    if conn is None:
        with connection() as c:
            return pd.read_sql_query(sql, c, params=params)
    return pd.read_sql_query(sql, conn, params=params)


def load_named_sql(path):
    """Parse a .sql file made of blocks:  -- name: x / -- table: y / -- desc: z / <statement>."""
    text = Path(path).read_text()
    blocks = re.split(r"(?m)^-- name:\s*", text)[1:]
    out = {}
    for b in blocks:
        name, _, rest = b.partition("\n")
        meta = {"table": "", "desc": ""}
        body = []
        for line in rest.splitlines():
            m = re.match(r"--\s*(table|desc):\s*(.*)", line)
            if m:
                meta[m.group(1)] = m.group(2).strip()
            elif line.startswith("-- ====") or not line.strip() and not body:
                continue
            else:
                body.append(line)
        out[name.strip()] = {"sql": "\n".join(body).strip().rstrip(";") + ";", **meta}
    return out


def run_script(conn, path):
    """Execute a whole .sql script (used for the schema)."""
    conn.executescript(Path(path).read_text())
    conn.commit()


def run_steps(conn, steps, only=None, verbose=True):
    """Execute named DML steps one by one, writing every step to audit_log. Returns a DataFrame."""
    log = []
    for name, st in steps.items():
        if only and name not in only:
            continue
        cur = conn.execute(st["sql"])
        n = cur.rowcount if cur.rowcount is not None else -1
        conn.execute("INSERT INTO audit_log (step, table_name, rows_affected, description) VALUES (?,?,?,?)",
                     (name, st["table"], n, st["desc"]))
        conn.commit()
        log.append({"step": name, "table": st["table"], "rows_affected": n, "description": st["desc"]})
        if verbose:
            print(f"[{name:<22}] {n:>7,} rows  - {st['desc']}")
    return pd.DataFrame(log)


def load_raw_csv(conn, csv_path):
    """CREATE/INSERT: bulk-load the CSV into raw_city_day (columns renamed, dates kept as ISO text)."""
    df = pd.read_csv(csv_path).rename(columns=COLUMN_MAP)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df.to_sql("raw_city_day", conn, if_exists="append", index=False)
    conn.commit()
    return len(df)


def populate_city_metadata(conn):
    """UPDATE (parameterised, many rows): add state and region to dim_city."""
    rows = [(STATE.get(c), REGION.get(c), c) for (c,) in conn.execute("SELECT city_name FROM dim_city")]
    conn.executemany("UPDATE dim_city SET state = ?, region = ? WHERE city_name = ?", rows)
    conn.commit()
    return len(rows)


def populate_festivals(conn):
    rows = [(f, d) for f, ds in FESTIVALS.items() for d in ds]
    conn.executemany("INSERT OR IGNORE INTO festival_calendar (festival, date) VALUES (?, ?)", rows)
    conn.commit()
    return len(rows)


def read_fact(conn=None, include_suspect=True):
    """Return fact table joined to city names, with parsed dates, sorted by city/date."""
    sql = "SELECT * FROM v_aqi_full" + ("" if include_suspect else " WHERE is_suspect = 0")
    df = query(sql, conn)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["city", "date"]).reset_index(drop=True)


def log_results(rows, task, conn=None):
    """Replace all stored results of `task` by `rows` (list of dicts: model, feature_set, eval_set, metric, value)."""
    own = conn is None
    conn = conn or get_conn()
    conn.execute("DELETE FROM model_results WHERE task = ?", (task,))
    conn.executemany(
        "INSERT INTO model_results (task, model, feature_set, eval_set, metric, value) VALUES (?,?,?,?,?,?)",
        [(task, r["model"], r["feature_set"], r["eval_set"], r["metric"], float(r["value"])) for r in rows])
    conn.commit()
    if own:
        conn.close()
