
import time

import pandas as pd

from cryptoscope.config import CryptoScopeConfig


class RiskService:

    def __init__(self, history_service):
        self.history = history_service
        self.symbols = set(CryptoScopeConfig.SYMBOLS)
        self.allowed_days = {30, 90, 365}
        self.cache = {}
        self.cache_duration = 60

    def get_analysis(self, symbol="BTCUSDT", days=365):

        if symbol not in self.symbols:
            raise ValueError("Unsupported cryptocurrency")

        if days not in self.allowed_days:
            raise ValueError("Choose 30, 90, or 365 days")

        key = (symbol, days)
        cached = self.cache.get(key)

        if cached and time.monotonic() - cached["time"] < 60:
            return cached["result"]

        # Read stored history and update it if necessary.
        hourly, stale = self.history.load_symbol(symbol)

        # Convert completed hourly candles into daily candles.
        daily = self.history.resample_candles(hourly, "1d")
        daily = daily.sort_values("open_time").copy()

        if len(daily) < 32:
            raise RuntimeError("Not enough historical daily candles")

        # Calculate daily percentage returns.
        daily["return"] = (
            daily["close"].astype(float)
            .pct_change(fill_method=None) * 100
        )

        # 30-day rolling volatility.
        daily["rolling_volatility"] = (
            daily["return"]
            .rolling(window=30, min_periods=30)
            .std()
        )

        df = daily.tail(days).dropna(subset=["return"]).copy()

        if len(df) < 2:
            raise RuntimeError("Not enough daily returns")

        avg = float(df["return"].mean())
        std = float(df["return"].std())

        # Identify statistically unusual returns.
        if std > 0:
            df["anomaly"] = (
                (df["return"] - avg).abs() > 2.5 * std
            )
        else:
            df["anomaly"] = False

        records = []

        for _, row in df.iterrows():
            rolling = row["rolling_volatility"]

            records.append({
                "time": row["open_time"].isoformat(),
                "return": round(float(row["return"]), 6),
                "rolling_volatility": (
                    round(float(rolling), 6)
                    if pd.notna(rolling)
                    else None
                ),
                "anomaly": bool(row["anomaly"])
            })

        result = {
            "symbol": symbol,
            "days_requested": days,
            "days_analyzed": len(df),
            "stale": stale,
            "source": "CryptoScope SQLite",
            "summary": {
                "mean_daily_return": round(avg, 4),
                "daily_volatility": round(std, 4),
                "positive_days": int((df["return"] > 0).sum()),
                "negative_days": int((df["return"] < 0).sum()),
                "unchanged_days": int((df["return"] == 0).sum()),
                "anomaly_count": int(df["anomaly"].sum()),
                "highest_return": round(
                    float(df["return"].max()), 4
                ),
                "lowest_return": round(
                    float(df["return"].min()), 4
                )
            },
            "records": records,
            "period_start": df["open_time"].min().isoformat(),
            "period_end": df["open_time"].max().isoformat()
        }

        self.cache[key] = {
            "time": time.monotonic(),
            "result": result
        }

        return result
