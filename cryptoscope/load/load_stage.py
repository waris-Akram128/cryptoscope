
from cryptoscope.load.database import DatabaseManager
from cryptoscope.load.candle_repository import CandleRepository
from cryptoscope.load.etl_log_repository import EtlLogRepository


class LoadStage:
    def __init__(self):
        self.database = DatabaseManager()
        self.candles = CandleRepository()
        self.log = EtlLogRepository()

    def run(self, clean_tables, rejected_tables, reports):
        """Load validated candles and logs into SQLite.

        Return run_id only after successful completion.
        Raise RuntimeError if loading fails.
        """

        print("STAGE 4: LOAD")

        # 1. Validate input dictionaries
        if not all(
            isinstance(data, dict)
            for data in (clean_tables, rejected_tables, reports)
        ):
            raise TypeError(
                "Load stage inputs must be dictionaries"
            )

        if not clean_tables:
            raise ValueError(
                "No validated candle tables to load"
            )

        symbols = set(clean_tables)

        if (
            set(rejected_tables) != symbols
            or set(reports) != symbols
        ):
            raise ValueError(
                "Load stage received mismatched symbols"
            )

        # 2. Create database tables
        if not self.database.create_tables():
            raise RuntimeError(
                "Could not create database tables"
            )

        # 3. Start ETL run log
        run_id = self.log.start_run()

        if run_id is None:
            raise RuntimeError(
                "Could not start ETL run log"
            )

        total_inserted = 0

        try:
            for symbol, df in clean_tables.items():

                print(f"  Loading {symbol}...")

                report = reports[symbol]
                rejected = rejected_tables[symbol]

                # 4. Save validation quality report
                quality_saved = self.log.save_quality(
                    run_id, report
                )

                if not quality_saved:
                    raise RuntimeError(
                        f"Could not save quality report for {symbol}"
                    )

                # 5. Save rejected candle rows
                if rejected is None:
                    raise RuntimeError(
                        f"Rejected DataFrame missing for {symbol}"
                    )

                saved_rejected = self.log.save_rejected(
                    run_id, symbol, rejected
                )

                if saved_rejected is None or saved_rejected != len(rejected):
                    raise RuntimeError(
                        f"Could not save all rejected rows for {symbol}")

                # 6. Save clean candles
                result = self.candles.save_candles(
                    df, symbol
                )

                if result is None:
                    raise RuntimeError(
                        f"Could not save candles for {symbol}"
                    )

                inserted, ignored = result
                total_inserted += inserted

                print(
                    f"  {symbol}: "
                    f"inserted={inserted}, "
                    f"ignored={ignored}, "
                    f"rejected_saved={saved_rejected}"
                )

            # 7. Mark completed run as SUCCESS
            finished = self.log.finish_run(
                run_id,
                "SUCCESS",
                total_inserted,
                "All coins loaded successfully"
            )

            if not finished:
                raise RuntimeError(
                    "Could not mark ETL run as SUCCESS"
                )

            print(
                f"\n  Run {run_id}: SUCCESS, "
                f"new candles={total_inserted}"
            )

            return run_id

        except Exception as e:

            # 8. Record failure in ETL log
            print(f"  Load stage failed: {e}")

            finished = self.log.finish_run(
                run_id,
                "FAILED",
                total_inserted,
                str(e)
            )

            if not finished:
                raise RuntimeError(
                    f"Load failed, and the ETL failure "
                    f"could not be logged for run {run_id}"
                ) from e

            # 9. Propagate error to main.py
            raise RuntimeError(
                f"Load stage failed (run {run_id}): {e}"
            ) from e
