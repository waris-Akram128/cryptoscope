
import sys
import traceback

from cryptoscope.config import CryptoScopeConfig
from cryptoscope.extract.raw_extractor import RawExtractor
from cryptoscope.transform.data_transformer import DataTransformer
from cryptoscope.validate.candle_validator import CandleValidator
from cryptoscope.load.load_stage import LoadStage


class CryptoScopePipeline:
    def __init__(self):
        self.extractor = RawExtractor()
        self.transformer = DataTransformer()
        self.validator = CandleValidator()
        self.loader = LoadStage()

    def check_symbols(self, data, stage):
        """Check that every configured symbol was processed."""

        if not isinstance(data, dict):
            raise RuntimeError(
                f"{stage}: Expected a dictionary"
            )

        expected = set(CryptoScopeConfig.SYMBOLS)
        received = set(data.keys())

        missing = expected - received

        if missing:
            raise RuntimeError(
                f"{stage}: Missing symbols: {sorted(missing)}"
            )

        extra = received - expected

        if extra:
            raise RuntimeError(
                f"{stage}: Unexpected symbols: {sorted(extra)}"
            )

        if any(value is None for value in data.values()):
            raise RuntimeError(
                f"{stage}: One or more symbols returned None"
            )

    def run(self):
        print("\n========== CRYPTOSCOPE ETL ==========\n")

        try:
            # STAGE 1: EXTRACT
            print("STAGE 1: EXTRACT")
            raw_data = self.extractor.run()
            self.check_symbols(raw_data, "EXTRACT")

            for symbol, candles in raw_data.items():
                if not candles:
                    raise RuntimeError(
                        f"EXTRACT: No candles for {symbol}"
                    )

            # STAGE 2: TRANSFORM
            tables = self.transformer.run(raw_data)
            self.check_symbols(tables, "TRANSFORM")

            # STAGE 3: VALIDATE
            clean_tables, rejected_tables, reports = (
                self.validator.run(tables)
            )

            self.check_symbols(clean_tables, "VALIDATE")
            self.check_symbols(rejected_tables, "REJECTED")
            self.check_symbols(reports, "REPORTS")

            # STAGE 4: LOAD
            run_id = self.loader.run(
                clean_tables,
                rejected_tables,
                reports
            )

            if run_id is None:
                raise RuntimeError(
                    "LOAD: Database run could not start"
                )

            print("\n========== PIPELINE COMPLETED ==========")
            print(f"Run ID: {run_id}")
            print("Check ETL log for final database status.")

            return run_id

        except Exception as e:
            print("\n========== PIPELINE FAILED ==========")
            print(f"Error: {e}")

            traceback.print_exc()
            raise


if __name__ == "__main__":
    try:
        CryptoScopePipeline().run()
    except Exception:
        sys.exit(1)
