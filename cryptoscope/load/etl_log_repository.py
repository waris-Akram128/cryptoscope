
from datetime import datetime, timezone
import pandas as pd

from cryptoscope.load.database import DatabaseManager

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class EtlLogRepository:
    def __init__(self):
        self.db = DatabaseManager()

    def start_run(self):
        """Create an ETL run and return its ID."""

        conn = self.db.get_connection()
        if conn is None:
            return None

        try:
            started = datetime.now(
                timezone.utc
            ).strftime(TIME_FORMAT)

            cursor = conn.execute(
                """
                INSERT INTO etl_run_log (started_at, status)
                VALUES (?, ?)
                """,
                (started, "RUNNING")
            )

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            conn.rollback()
            print("Start run error:", e)
            return None

        finally:
            conn.close()

    def finish_run(
        self,
        run_id,
        status,
        rows_loaded,
        message=""
    ):
        """Update the ETL run with its final status."""

        conn = self.db.get_connection()
        if conn is None:
            return False

        try:
            finished = datetime.now(
                timezone.utc
            ).strftime(TIME_FORMAT)

            cursor = conn.execute(
                """
                UPDATE etl_run_log
                SET finished_at = ?,
                    status = ?,
                    rows_loaded = ?,
                    message = ?
                WHERE run_id = ?
                """,
                (
                    finished,
                    status,
                    rows_loaded,
                    message,
                    run_id
                )
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return False

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print("Finish run error:", e)
            return False

        finally:
            conn.close()

    def save_quality(self, run_id, report):
        """Save one cryptocurrency's quality report."""

        conn = self.db.get_connection()
        if conn is None:
            return False

        try:
            conn.execute(
                """
                INSERT INTO data_quality (
                    run_id,
                    symbol,
                    rows_in,
                    duplicates_removed,
                    rows_rejected,
                    missing_hours,
                    rows_clean
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    report["symbol"],
                    report["rows_in"],
                    report["duplicates_removed"],
                    report["rows_rejected"],
                    report["missing_hours"],
                    report["rows_clean"]
                )
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print("Save quality error:", e)
            return False

        finally:
            conn.close()

    def save_rejected(self, run_id, symbol, rejected):
        """
        Save rejected candles.

        Return:
            int: Number of rows saved.
            None: Database operation failed.
        """

        if rejected is None:
            return None

        if len(rejected) == 0:
            return 0

        conn = self.db.get_connection()
        if conn is None:
            return None

        try:
            rows = []

            for r in rejected.itertuples(index=False):

                # Handle invalid or missing timestamps safely
                timestamp = pd.to_datetime(
                    r.open_time,
                    utc=True,
                    errors="coerce"
                )

                if pd.isna(timestamp):
                    open_time = None
                else:
                    open_time = timestamp.strftime(
                        TIME_FORMAT
                    )

                rows.append(
                    (
                        run_id,
                        symbol,
                        open_time,
                        str(r.reason)
                    )
                )

            conn.executemany(
                """
                INSERT INTO rejected_rows (
                    run_id,
                    symbol,
                    open_time,
                    reason
                )
                VALUES (?, ?, ?, ?)
                """,
                rows
            )

            conn.commit()
            return len(rows)

        except Exception as e:
            conn.rollback()
            print(
                f"Save rejected error for {symbol}: {e}"
            )
            return None

        finally:
            conn.close()
