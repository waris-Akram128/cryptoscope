
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

            # 3. Create DataFrames (preserve columns if empty)
            clean = pd.DataFrame(good_rows, columns=df.columns)
            clean = clean.sort_values("open_time").reset_index(drop=True)

            rejected = pd.DataFrame(
                rejected_rows,
                columns=[*df.columns, "reason"]
            )

            # 4. Find missing hours safely
            if clean.empty:
                missing_hours = 0
            else:
                expected = pd.date_range(
                    start=clean["open_time"].min(),
                    end=clean["open_time"].max(),
                    freq="1h"
                )

                missing = expected.difference(
                    pd.DatetimeIndex(clean["open_time"])
                )

                missing_hours = len(missing)

            # 5. Generate validation report
            report = {
                "symbol": symbol,
                "rows_in": rows_in,
                "duplicates_removed": duplicates,
                "rows_rejected": len(rejected),
                "missing_hours": missing_hours,
                "rows_clean": len(clean),
            }

            return clean, rejected, report

        except Exception as e:
            raise RuntimeError(
                f"Validation failed for {symbol}: {e}"
            ) from e

    def run(self, tables):
        """Validate every coin. Return (clean_tables, rejected_tables, reports)."""

        print("STAGE 3: VALIDATE")

        clean_tables = {}
        rejected_tables = {}
        reports = {}

        for symbol, df in tables.items():
            clean, rejected, report = self.validate(df, symbol)

            clean_tables[symbol] = clean
            rejected_tables[symbol] = rejected
            reports[symbol] = report

            print(
                f"  {symbol}: "
                f"clean={report['rows_clean']}, "
                f"duplicates={report['duplicates_removed']}, "
                f"rejected={report['rows_rejected']}, "
                f"missing_hours={report['missing_hours']}"
            )

        return clean_tables, rejected_tables, reports
