import pandas as pd
from pydantic import ValidationError
from cryptoscope.validate.data_models import CandleModel


class CandleValidator:
    def validate(self, df, symbol):
        """Validate one coin. Return (clean_df, rejected_df, report)."""
        try:
            rows_in = len(df)

            # 1. Remove duplicate candles
            df = df.drop_duplicates(subset=["symbol", "open_time"])
            duplicates = rows_in - len(df)

            # 2. Check every row with Pydantic
            good_rows = []
            rejected_rows = []

            for row in df.to_dict("records"):
                try:
                    CandleModel(**row)
                    good_rows.append(row)
                except ValidationError as e:
                    row["reason"] = e.errors()[0]["msg"]
                    rejected_rows.append(row)

            clean = pd.DataFrame(good_rows)
            clean = clean.sort_values("open_time").reset_index(drop=True)
            rejected = pd.DataFrame(rejected_rows)

            # 3. Find missing hours
            expected = pd.date_range(
                clean["open_time"].min(), clean["open_time"].max(), freq="1h"
            )
            missing = expected.difference(pd.DatetimeIndex(clean["open_time"]))

            report = {
                "symbol": symbol,
                "rows_in": rows_in,
                "duplicates_removed": duplicates,
                "rows_rejected": len(rejected),
                "missing_hours": len(missing),
                "rows_clean": len(clean),
            }
            return clean, rejected, report

        except Exception as e:
            print("Validate error for", symbol, ":", e)
            return None, None, None

    def run(self, tables):
        """Validate every coin. Return (clean_tables, rejected_tables, reports)."""
        print("STAGE 3: VALIDATE")
        clean_tables = {}
        rejected_tables = {}
        reports = {}

        try:
            for symbol, df in tables.items():
                clean, rejected, report = self.validate(df, symbol)
                if report is None:
                    continue

                clean_tables[symbol] = clean
                rejected_tables[symbol] = rejected
                reports[symbol] = report
                print(f"  {symbol}: clean={report['rows_clean']}, "
                      f"duplicates={report['duplicates_removed']}, "
                      f"rejected={report['rows_rejected']}, "
                      f"missing_hours={report['missing_hours']}")

        except Exception as e:
            print("Validate stage failed:", e)

        return clean_tables, rejected_tables, reports