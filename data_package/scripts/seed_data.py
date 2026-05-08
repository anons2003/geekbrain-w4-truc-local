"""
GeekBrain Data Seeder
Reads CSV files from ../structured_data/ and loads them into PostgreSQL or SQLite.

Usage:
  python seed_data.py --db-type sqlite                          # SQLite (default path: geekbrain.db)
  python seed_data.py --db-type sqlite --sqlite-path /tmp/gb.db
  python seed_data.py --db-type postgres --db-url postgresql://user:pass@localhost/geekbrain
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "structured_data"

CREATE_STATEMENTS = {
    "monthly_costs": """
        CREATE TABLE IF NOT EXISTS monthly_costs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            service           TEXT NOT NULL,
            month             TEXT NOT NULL,
            compute_cost      REAL NOT NULL,
            storage_cost      REAL NOT NULL,
            network_cost      REAL NOT NULL,
            third_party_cost  REAL NOT NULL,
            total_cost        REAL NOT NULL,
            UNIQUE(service, month)
        )
    """,
    "incidents": """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id       TEXT PRIMARY KEY,
            service           TEXT NOT NULL,
            date              TEXT NOT NULL,
            severity          TEXT NOT NULL,
            duration_minutes  INTEGER NOT NULL,
            root_cause        TEXT NOT NULL,
            resolution        TEXT NOT NULL,
            team_responsible  TEXT NOT NULL,
            reported_by       TEXT NOT NULL
        )
    """,
    "sla_targets": """
        CREATE TABLE IF NOT EXISTS sla_targets (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            service            TEXT NOT NULL,
            metric             TEXT NOT NULL,
            target             REAL NOT NULL,
            measurement_window TEXT NOT NULL,
            UNIQUE(service, metric)
        )
    """,
    "daily_metrics": """
        CREATE TABLE IF NOT EXISTS daily_metrics (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            date                  TEXT NOT NULL,
            service               TEXT NOT NULL,
            latency_p99_ms        REAL NOT NULL,
            error_rate_percent    REAL NOT NULL,
            requests_per_minute   INTEGER NOT NULL,
            availability_percent  REAL NOT NULL,
            UNIQUE(date, service)
        )
    """,
}

POSTGRES_CREATE = {
    "monthly_costs": """
        CREATE TABLE IF NOT EXISTS monthly_costs (
            id                SERIAL PRIMARY KEY,
            service           VARCHAR(64) NOT NULL,
            month             VARCHAR(7) NOT NULL,
            compute_cost      NUMERIC(12,2) NOT NULL,
            storage_cost      NUMERIC(12,2) NOT NULL,
            network_cost      NUMERIC(12,2) NOT NULL,
            third_party_cost  NUMERIC(12,2) NOT NULL,
            total_cost        NUMERIC(12,2) NOT NULL,
            UNIQUE(service, month)
        )
    """,
    "incidents": """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id       VARCHAR(16) PRIMARY KEY,
            service           VARCHAR(64) NOT NULL,
            date              DATE NOT NULL,
            severity          VARCHAR(4) NOT NULL,
            duration_minutes  INTEGER NOT NULL,
            root_cause        TEXT NOT NULL,
            resolution        TEXT NOT NULL,
            team_responsible  VARCHAR(64) NOT NULL,
            reported_by       VARCHAR(64) NOT NULL
        )
    """,
    "sla_targets": """
        CREATE TABLE IF NOT EXISTS sla_targets (
            id                 SERIAL PRIMARY KEY,
            service            VARCHAR(64) NOT NULL,
            metric             VARCHAR(64) NOT NULL,
            target             NUMERIC(10,4) NOT NULL,
            measurement_window VARCHAR(32) NOT NULL,
            UNIQUE(service, metric)
        )
    """,
    "daily_metrics": """
        CREATE TABLE IF NOT EXISTS daily_metrics (
            id                    SERIAL PRIMARY KEY,
            date                  DATE NOT NULL,
            service               VARCHAR(64) NOT NULL,
            latency_p99_ms        NUMERIC(10,2) NOT NULL,
            error_rate_percent    NUMERIC(10,4) NOT NULL,
            requests_per_minute   INTEGER NOT NULL,
            availability_percent  NUMERIC(10,4) NOT NULL,
            UNIQUE(date, service)
        )
    """,
}

INSERTS = {
    "monthly_costs": (
        "INSERT OR IGNORE INTO monthly_costs (service, month, compute_cost, storage_cost, network_cost, third_party_cost, total_cost) VALUES (?,?,?,?,?,?,?)",
        lambda r: (r["service"], r["month"], float(r["compute_cost"]), float(r["storage_cost"]), float(r["network_cost"]), float(r["third_party_cost"]), float(r["total_cost"])),
    ),
    "incidents": (
        "INSERT OR IGNORE INTO incidents (incident_id, service, date, severity, duration_minutes, root_cause, resolution, team_responsible, reported_by) VALUES (?,?,?,?,?,?,?,?,?)",
        lambda r: (r["incident_id"], r["service"], r["date"], r["severity"], int(r["duration_minutes"]), r["root_cause"], r["resolution"], r["team_responsible"], r["reported_by"]),
    ),
    "sla_targets": (
        "INSERT OR IGNORE INTO sla_targets (service, metric, target, measurement_window) VALUES (?,?,?,?)",
        lambda r: (r["service"], r["metric"], float(r["target"]), r["measurement_window"]),
    ),
    "daily_metrics": (
        "INSERT OR IGNORE INTO daily_metrics (date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent) VALUES (?,?,?,?,?,?)",
        lambda r: (r["date"], r["service"], float(r["latency_p99_ms"]), float(r["error_rate_percent"]), int(r["requests_per_minute"]), float(r["availability_percent"])),
    ),
}

POSTGRES_INSERTS = {
    "monthly_costs": "INSERT INTO monthly_costs (service, month, compute_cost, storage_cost, network_cost, third_party_cost, total_cost) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (service, month) DO NOTHING",
    "incidents": "INSERT INTO incidents (incident_id, service, date, severity, duration_minutes, root_cause, resolution, team_responsible, reported_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (incident_id) DO NOTHING",
    "sla_targets": "INSERT INTO sla_targets (service, metric, target, measurement_window) VALUES (%s,%s,%s,%s) ON CONFLICT (service, metric) DO NOTHING",
    "daily_metrics": "INSERT INTO daily_metrics (date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (date, service) DO NOTHING",
}


def load_csv(table_name: str):
    path = DATA_DIR / f"{table_name}.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed_sqlite(sqlite_path: str):
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    for table, ddl in CREATE_STATEMENTS.items():
        cur.execute(ddl)

    totals = {}
    for table, (sql, row_fn) in INSERTS.items():
        rows = load_csv(table)
        params = [row_fn(r) for r in rows]
        cur.executemany(sql, params)
        totals[table] = len(params)

    conn.commit()
    conn.close()
    return totals


def seed_postgres(db_url: str):
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for table, ddl in POSTGRES_CREATE.items():
        cur.execute(ddl)

    totals = {}
    for table, sql in POSTGRES_INSERTS.items():
        rows = load_csv(table)
        row_fn = INSERTS[table][1]
        params = [row_fn(r) for r in rows]
        cur.executemany(sql, params)
        totals[table] = len(params)

    conn.commit()
    cur.close()
    conn.close()
    return totals


def main():
    parser = argparse.ArgumentParser(description="Seed GeekBrain structured data into a database.")
    parser.add_argument("--db-type", choices=["postgres", "sqlite"], default="sqlite", help="Database type (default: sqlite)")
    parser.add_argument("--db-url", help="PostgreSQL connection URL (postgres mode only)")
    parser.add_argument("--sqlite-path", default="geekbrain.db", help="SQLite file path (default: geekbrain.db)")
    args = parser.parse_args()

    if args.db_type == "sqlite":
        print(f"Seeding SQLite: {args.sqlite_path}")
        totals = seed_sqlite(args.sqlite_path)
    else:
        if not args.db_url:
            print("Error: --db-url is required for postgres mode.")
            sys.exit(1)
        print(f"Seeding PostgreSQL: {args.db_url}")
        totals = seed_postgres(args.db_url)

    print("\nRow counts loaded:")
    for table, count in totals.items():
        print(f"  {table}: {count} rows")
    print("\nDone.")


if __name__ == "__main__":
    main()
