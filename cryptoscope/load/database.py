import os
import sqlite3
from cryptoscope.config import CryptoScopeConfig

SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_asset (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol   TEXT NOT NULL UNIQUE,
    name     TEXT
);

CREATE TABLE IF NOT EXISTS fact_candles_1h (
    asset_id     INTEGER NOT NULL,
    open_time    TEXT NOT NULL,
    open         REAL NOT NULL,
    high         REAL NOT NULL,
    low          REAL NOT NULL,
    close        REAL NOT NULL,
    volume       REAL NOT NULL,
    quote_volume REAL NOT NULL,
    trades       INTEGER NOT NULL,
    PRIMARY KEY (asset_id, open_time),
    FOREIGN KEY (asset_id) REFERENCES dim_asset (asset_id)
);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT,
    rows_loaded INTEGER,
    message     TEXT
);

CREATE TABLE IF NOT EXISTS data_quality (
    quality_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER,
    symbol             TEXT NOT NULL,
    rows_in            INTEGER,
    duplicates_removed INTEGER,
    rows_rejected      INTEGER,
    missing_hours      INTEGER,
    rows_clean         INTEGER,
    FOREIGN KEY (run_id) REFERENCES etl_run_log (run_id)
);

CREATE TABLE IF NOT EXISTS rejected_rows (
    rejected_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER,
    symbol      TEXT NOT NULL,
    open_time   TEXT,
    reason      TEXT,
    FOREIGN KEY (run_id) REFERENCES etl_run_log (run_id)
);
"""


class DatabaseManager:
    def __init__(self):
        self.db_path = CryptoScopeConfig.DATABASE_PATH

    def get_connection(self):
        """Open the SQLite file (it is created if it does not exist)."""
        try:
            folder = os.path.dirname(self.db_path)
            if folder:
                os.makedirs(folder, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")   # enforce foreign keys
            return conn

        except Exception as e:
            print("Database connection error:", e)
            return None

    def create_tables(self):
        """Create all five tables. Safe to run many times."""
        conn = self.get_connection()
        if conn is None:
            return False

        try:
            conn.executescript(SCHEMA)
            conn.commit()
            return True

        except Exception as e:
            print("Create tables error:", e)
            return False

        finally:
            conn.close()      # always runs, even after an error