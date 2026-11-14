
import threading
import time
from datetime import datetime, timezone

import pandas as pd

from cryptoscope.config import CryptoScopeConfig
from cryptoscope.extract.binance_client import BinanceClient
from cryptoscope.transform.data_transformer import DataTransformer
from cryptoscope.validate.candle_validator import CandleValidator
from cryptoscope.load.candle_repository import CandleRepository
from cryptoscope.analysis.data_reader import CandleDataReader


class HistoryService:

    def __init__(self):
        self.client = BinanceClient()
        self.transformer = DataTransformer()
        self.validator = CandleValidator()
        self.repository = CandleRepository()
        self.reader = CandleDataReader()

        self.symbols = set(CryptoScopeConfig.SYMBOLS)

        self.intervals = {
            "1h": ("1h", 1),
            "4h": ("4h", 4),
            "1d": ("1D", 24)
        }

        self.allowed_limits = {
            48, 168, 336, 365, 500, 8760
        }

        self.cache = {}
        self.cache_duration = 60

        # One lock for each cryptocurrency.
        self.locks = {
            symbol: threading.Lock()
            for symbol in self.symbols
        }

    def load_symbol(self, symbol):
        """
        Update one cryptocurrency and cache its
        historical DataFrame for 60 seconds.
        """

        if symbol not in self.symbols:
            raise ValueError("Unsupported cryptocurrency")

        with self.locks[symbol]:

            cached = self.cache.get(symbol)

            # Return cached DataFrame when valid.
            if cached is not None:
                age = time.monotonic() - cached["time"]

                if age < self.cache_duration:
                    return (
                        cached["data"],
                        cached["stale"]
                    )

            # Read latest stored candle timestamp.
            latest = self.repository.get_latest_candle_time(
                symbol
            )

            if latest is None:
                raise RuntimeError(
                    f"No stored data for {symbol}. "
                    "Run the ETL pipeline first."
                )

            stale = False

            # Fetch only new completed hourly candles.
            try:
                new_raw = self.client.get_new_klines(
                    symbol,
                    latest,
                    "1h"
                )

                if new_raw:

                    # Transform new candles.
                    transformed = self.transformer.transform(
                        new_raw,
                        symbol
                    )

                    # Validate new candles.
                    clean, rejected, report = (
                        self.validator.validate(
                            transformed,
                            symbol
                        )
                    )

                    if not clean.empty:
                        result = self.repository.save_candles(
                            clean,
                            symbol
                        )

                        if result is None:
                            raise RuntimeError(
                                "Database insertion failed"
                            )

                        inserted, ignored = result

                        print(
                            f"{symbol}: inserted={inserted}, "
                            f"ignored={ignored}"
                        )

                    if (
                        len(rejected) > 0
                        or report["missing_hours"] > 0
                    ):
                        stale = True

            except Exception as e:
                print(
                    f"{symbol}: update failed: {e}"
                )

                # Continue with stored historical data.
                stale = True

            # Read only a limited historical window.
            now = pd.Timestamp.now(tz="UTC")

            # Extra days allow complete daily resampling.
            start = now - pd.Timedelta(days=367)

            df = self.reader.get_candles(
                symbol=symbol,
                start=start
            )

            if df.empty:
                raise RuntimeError(
                    f"No historical records for {symbol}"
                )

            df["open_time"] = pd.to_datetime(
                df["open_time"],
                utc=True
            )

            numeric_columns = [
                "open", "high", "low", "close",
                "volume", "quote_volume", "trades"
            ]

            for column in numeric_columns:
                df[column] = pd.to_numeric(
                    df[column],
                    errors="raise"
                )

            # Exclude currently unfinished hourly candle.
            current_hour = now.floor("h")

            df = df[
                df["open_time"] < current_hour
            ]

            df = (
                df.drop_duplicates(
                    subset=["symbol", "open_time"],
                    keep="last"
                )
                .sort_values("open_time")
                .reset_index(drop=True)
            )

            # Cache complete DataFrame.
            self.cache[symbol] = {
                "data": df,
                "stale": stale,
                "time": time.monotonic()
            }

            return df, stale

    def resample_candles(self, df, interval):
        """Convert hourly candles to 4h or daily."""

        if interval == "1h":
            return df

        frequency, hours = self.intervals[interval]

        indexed = df.set_index("open_time")

        grouped = indexed.resample(
            frequency,
            label="left",
            closed="left"
        )

        result = grouped.agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "quote_volume": "sum",
            "trades": "sum"
        })

        counts = grouped["close"].count()

        # Keep only groups with every hourly candle.
        result = result[counts == hours]

        now = pd.Timestamp.now(tz="UTC")
        current_period = now.floor(frequency)

        result = result[
            result.index < current_period
        ]

        return result.reset_index()

    def get_candles(
        self,
        symbol,
        interval="1h",
        limit=168
    ):
        """Return cached, updated historical candles."""

        if symbol not in self.symbols:
            raise ValueError("Unsupported cryptocurrency")

        if interval not in self.intervals:
            raise ValueError("Unsupported interval")

        if limit not in self.allowed_limits:
            raise ValueError("Unsupported candle count")

        # DataFrame is cached across dashboard requests.
        hourly, stale = self.load_symbol(symbol)

        df = self.resample_candles(
            hourly,
            interval
        )

        # Return at most the latest year.
        now = pd.Timestamp.now(tz="UTC")

        if interval == "1d":
            cutoff = (
                now.floor("D")
                - pd.Timedelta(days=365)
            )
        else:
            cutoff = now - pd.Timedelta(days=365)

        df = df[
            df["open_time"] >= cutoff
        ].tail(limit)

        if df.empty:
            raise RuntimeError(
                f"No completed candles for {symbol}"
            )

        first = df.iloc[0]
        last = df.iloc[-1]

        first_open = float(first["open"])

        change = (
            (float(last["close"]) / first_open - 1)
            * 100
        ) if first_open else 0

        candles = [
            {
                "time": row.open_time.isoformat(),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
                "quote_volume": float(row.quote_volume),
                "trades": int(row.trades)
            }
            for row in df.itertuples(index=False)
        ]

        return {
            "symbol": symbol,
            "interval": interval,
            "source": "SQLite",
            "stale": stale,
            "candles": candles,
            "summary": {
                "latest_price": float(last["close"]),
                "change": change,
                "highest": float(df["high"].max()),
                "lowest": float(df["low"].min()),
                "quote_volume": float(
                    df["quote_volume"].sum()
                ),
                "total_trades": int(
                    df["trades"].sum()
                )
            },
            "latest_candle_time": (
                last["open_time"].isoformat()
            ),
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat()
        }
