
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

import pandas as pd

from cryptoscope.config import CryptoScopeConfig
from dashboard.services.history_service import HistoryService


class AnalyticsService:

    def __init__(self, history_service):
        self.history = history_service
        self.symbols = list(CryptoScopeConfig.SYMBOLS)
        self.allowed_days = {30, 90, 365}

    def get_correlation(self, days=30):
        """Calculate correlation of daily returns from SQLite."""

        if days not in self.allowed_days:
            raise ValueError("Choose 30, 90, or 365 days")

        # Load all five assets concurrently.
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(
                executor.map(
                    self.history.load_symbol,
                    self.symbols
                )
            )

        price_series = {}
        stale_symbols = []

        for symbol, (hourly_df, stale) in zip(
            self.symbols, results
        ):
            if stale:
                stale_symbols.append(symbol)

            # Use the existing history service to
            # convert hourly data into complete daily candles.
            daily = self.history.resample_candles(
                hourly_df,
                "1d"
            )

            if daily.empty:
                raise RuntimeError(
                    f"No complete daily candles for {symbol}"
                )

            daily = daily.set_index("open_time")

            price_series[symbol] = daily["close"].astype(float)

        # Align all assets using matching UTC dates.
        prices = pd.concat(
            price_series,
            axis=1
        ).dropna()

        # Need one additional price to calculate returns.
        prices = prices.tail(days + 1)

        if len(prices) < 3:
            raise RuntimeError(
                "Not enough matching daily candles"
            )

        returns = prices.pct_change().dropna() * 100

        if len(returns) < 2:
            raise RuntimeError(
                "Not enough returns for correlation"
            )

        matrix = returns.corr()

        names = [
            symbol.replace("USDT", "")
            for symbol in self.symbols
        ]

        # Convert correlation values to JSON-safe numbers.
        values = []

        for row_symbol in self.symbols:
            row = []

            for col_symbol in self.symbols:
                value = matrix.loc[row_symbol, col_symbol]

                row.append(
                    round(float(value), 4)
                    if pd.notna(value)
                    else None
                )

            values.append(row)

        # Find strongest and weakest pairs.
        pairs = []

        for first, second in combinations(self.symbols, 2):
            value = matrix.loc[first, second]

            if pd.notna(value):
                pairs.append({
                    "first": first.replace("USDT", ""),
                    "second": second.replace("USDT", ""),
                    "correlation": round(float(value), 4)
                })

        strongest = (
            max(pairs, key=lambda x: x["correlation"])
            if pairs else None
        )

        weakest = (
            min(pairs, key=lambda x: x["correlation"])
            if pairs else None
        )

        # Per-asset daily return volatility.
        volatilities = {}

        for symbol in self.symbols:
            value = returns[symbol].std()

            volatilities[symbol.replace("USDT", "")] = (
                round(float(value), 4)
                if pd.notna(value)
                else None
            )

        return {
            "days_requested": days,
            "days_analyzed": len(returns),
            "assets": names,
            "matrix": values,
            "strongest_pair": strongest,
            "weakest_pair": weakest,
            "volatility": volatilities,
            "period_start": returns.index.min().isoformat(),
            "period_end": returns.index.max().isoformat(),
            "stale": bool(stale_symbols),
            "stale_symbols": stale_symbols,
            "source": "CryptoScope SQLite",
            "method": "Pearson correlation of daily returns"
        }
