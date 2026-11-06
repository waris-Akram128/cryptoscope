from cryptoscope.load.database import DatabaseManager
from cryptoscope.load.candle_repository import CandleRepository
from cryptoscope.load.etl_log_repository import EtlLogRepository


class LoadStage:
    def __init__(self):
        self.database = DatabaseManager()
        self.candles = CandleRepository()
        self.log = EtlLogRepository()

    def run(self, clean_tables, rejected_tables, reports):
        """Load everything into SQLite. Return the run_id, or None if it could not start."""
        print("STAGE 4: LOAD")

        if not self.database.create_tables():
            print("  Could not create tables. Load stopped.")
            return None

        run_id = self.log.start_run()
        if run_id is None:
            print("  Could not start the run log. Load stopped.")
            return None

        total_inserted = 0
        failed = []

        try:
            for symbol, df in clean_tables.items():
                # 1. Record what validation found
                report = reports.get(symbol)
                if report is not None:
                    self.log.save_quality(run_id, report)
                saved_rejected = self.log.save_rejected(
                    run_id, symbol, rejected_tables.get(symbol)
                )

                # 2. Save the candles
                result = self.candles.save_candles(df, symbol)
                if result is None:
                    failed.append(symbol)
                    continue

                inserted, ignored = result
                total_inserted += inserted
                print(f"  {symbol}: inserted={inserted}, ignored={ignored}, "
                      f"rejected saved={saved_rejected}")

            if failed:
                status = "FAILED"
                message = "Could not save: " + ", ".join(failed)
            else:
                status = "SUCCESS"
                message = "All coins loaded"

        except Exception as e:
            status = "FAILED"
            message = str(e)
            print("Load stage failed:", e)

        self.log.finish_run(run_id, status, total_inserted, message)
        print(f"  Run {run_id}: {status}, new candles={total_inserted}")
        return run_id