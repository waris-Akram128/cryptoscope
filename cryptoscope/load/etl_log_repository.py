from datetime import datetime, timezone
from cryptoscope.load.database import DatabaseManager

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class EtlLogRepository:
    def __init__(self):
        self.db = DatabaseManager()

    def start_run(self):
        """Create a new run record. Return its run_id, or None on error."""
        conn = self.db.get_connection()
        if conn is None:
            return None

        try:
            started = datetime.now(timezone.utc).strftime(TIME_FORMAT)
            cursor = conn.execute(
                "INSERT INTO etl_run_log (started_at, status) VALUES (?, ?)",
                (started, "RUNNING"),
            )
            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            conn.rollback()
            print("Start run error:", e)
            return None

        finally:
            conn.close()

    def finish_run(self, run_id, status, rows_loaded, message=""):
        """Close the run record with its final status."""
        conn = self.db.get_connection()
        if conn is None:
            return False

        try:
            finished = datetime.now(timezone.utc).strftime(TIME_FORMAT)
            conn.execute(
                "UPDATE etl_run_log "
                "SET finished_at = ?, status = ?, rows_loaded = ?, message = ? "
                "WHERE run_id = ?",
                (finished, status, rows_loaded, message, run_id),
            )
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print("Finish run error:", e)
            return False

        finally:
            conn.close()

    def save_quality(self, run_id, report):
        """Save one coin's validation report."""
        conn = self.db.get_connection()
        if conn is None:
            return False

        try:
            conn.execute(
                "INSERT INTO data_quality "
                "(run_id, symbol, rows_in, duplicates_removed, "
                " rows_rejected, missing_hours, rows_clean) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    report["symbol"],
                    report["rows_in"],
                    report["duplicates_removed"],
                    report["rows_rejected"],
                    report["missing_hours"],
                    report["rows_clean"],
                ),
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
        """Save the rejected candles of one coin. Return how many were saved."""
        if rejected is None or len(rejected) == 0:
            return 0

        conn = self.db.get_connection()
        if conn is None:
            return 0

        try:
            rows = []
            for r in rejected.itertuples(index=False):
                rows.append((
                    run_id,
                    symbol,
                    r.open_time.strftime(TIME_FORMAT),
                    r.reason,
                ))

            conn.executemany(
                "INSERT INTO rejected_rows (run_id, symbol, open_time, reason) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            return len(rows)

        except Exception as e:
            conn.rollback()
            print("Save rejected error:", e)
            return 0

        finally:
            conn.close()