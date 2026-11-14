
import pandas as pd


class DataTransformer:
    def __init__(self):
        # Raw position -> new column name
        self.columns = {
            0: "open_time",
            1: "open",
            2: "high",
            3: "low",
            4: "close",
            5: "volume",
            7: "quote_volume",
            8: "trades",
        }

    def transform(self, candles, symbol):
        """Convert raw Binance candles into a DataFrame."""

        try:
            # 1. Check the input
            if not isinstance(candles, list):
                raise TypeError(
                    "Candles must be provided as a list"
                )

            if not candles:
                raise ValueError(
                    "Candle list is empty"
                )

            # 2. Convert raw data into a DataFrame
            df = pd.DataFrame(candles)

            # 3. Check required column positions
            required_columns = list(self.columns.keys())

            missing_columns = [
                col for col in required_columns
                if col not in df.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"Missing raw columns: {missing_columns}"
                )

            # 4. Keep required columns and rename them
            df = df[required_columns].copy()
            df = df.rename(columns=self.columns)

            # 5. Convert price and volume values
            numeric_columns = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
            ]

            for name in numeric_columns:
                df[name] = df[name].astype(float)

            # 6. Convert trade count to integer
            df["trades"] = df["trades"].astype(int)

            # 7. Convert milliseconds to UTC datetime
            df["open_time"] = pd.to_datetime(
                df["open_time"],
                unit="ms",
                utc=True,
                errors="raise"
            )

            # 8. Add cryptocurrency symbol
            df.insert(0, "symbol", symbol)

            return df

        except Exception as e:
            raise RuntimeError(
                f"Transformation failed for {symbol}: {e}"
            ) from e

    def run(self, raw_data):
        """Transform all coins or raise an error."""

        print("STAGE 2: TRANSFORM")

        if not isinstance(raw_data, dict):
            raise TypeError(
                "Raw data must be a dictionary"
            )

        if not raw_data:
            raise ValueError(
                "No raw data available for transformation"
            )

        tables = {}

        for symbol, candles in raw_data.items():

            # Errors propagate automatically
            df = self.transform(candles, symbol)

            tables[symbol] = df

            print(
                f"  {symbol}: "
                f"{df.shape[0]} rows, "
                f"{df.shape[1]} columns"
            )

        return tables
