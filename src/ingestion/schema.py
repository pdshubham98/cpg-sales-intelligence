import sqlite3
import os
from pathlib import Path


def get_connection() -> sqlite3.Connection:
    # Read DB_PATH at call time so tests can patch it via os.environ.
    db_path = Path(os.getenv("DB_PATH", "db/sales.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS regions (
                region_id    TEXT PRIMARY KEY,
                region_name  TEXT NOT NULL,
                country      TEXT NOT NULL,
                sales_manager TEXT
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id   TEXT PRIMARY KEY,
                sku          TEXT NOT NULL UNIQUE,
                product_name TEXT NOT NULL,
                category     TEXT NOT NULL,
                unit_price   REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales_transactions (
                transaction_id TEXT PRIMARY KEY,
                date           TEXT NOT NULL,
                region_id      TEXT NOT NULL REFERENCES regions(region_id),
                product_id     TEXT NOT NULL REFERENCES products(product_id),
                sku            TEXT NOT NULL,
                quantity       REAL NOT NULL,
                unit_price     REAL NOT NULL,
                discount_pct   REAL NOT NULL DEFAULT 0.0,
                channel        TEXT NOT NULL,
                revenue        REAL NOT NULL,
                source         TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_sales_date     ON sales_transactions(date);
            CREATE INDEX IF NOT EXISTS idx_sales_region   ON sales_transactions(region_id);
            CREATE INDEX IF NOT EXISTS idx_sales_product  ON sales_transactions(product_id);
        """)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                raw_rows    INTEGER,
                clean_rows  INTEGER,
                dropped_rows INTEGER,
                sources     TEXT
            );
        """)
        # Migrate: add source column if the table pre-dates this change
        existing = {row[1] for row in conn.execute("PRAGMA table_info(sales_transactions)")}
        if "source" not in existing:
            conn.execute("ALTER TABLE sales_transactions ADD COLUMN source TEXT")
