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
        """Turn a raw list of candles into a clean DataFrame."""
        try:
            # 1. Raw list of lists -> table
            df = pd.DataFrame(candles)

            # 2. Keep only the 8 columns we need, and give them names
            df = df[list(self.columns.keys())]
            df = df.rename(columns=self.columns)

            # 3. Convert text to numbers
            for name in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[name] = df[name].astype(float)
            df["trades"] = df["trades"].astype(int)

            # 4. Convert milliseconds to a real date and time
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

            # 5. Remember which coin this is
            df.insert(0, "symbol", symbol)

            return df

        except Exception as e:
            print("Transform error for", symbol, ":", e)
            return None

    def run(self, raw_data):
        """Transform every coin. Return {symbol: DataFrame}."""
        print("STAGE 2: TRANSFORM")
        tables = {}

        try:
            for symbol, candles in raw_data.items():
                df = self.transform(candles, symbol)
                if df is not None:
                    tables[symbol] = df
                    print(f"  {symbol}: {df.shape[0]} rows, {df.shape[1]} columns")

        except Exception as e:
            print("Transform stage failed:", e)

        return tables