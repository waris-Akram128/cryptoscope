
import threading
import time
from datetime import datetime, timezone

import requests

from cryptoscope.config import CryptoScopeConfig


class MarketService:

    def __init__(self):
        self.url = "https://api.binance.com/api/v3/ticker/24hr"

        self.symbols = CryptoScopeConfig.SYMBOLS

        self.asset_names = {
            "BTCUSDT": "Bitcoin",
            "ETHUSDT": "Ethereum",
            "SOLUSDT": "Solana",
            "BNBUSDT": "BNB",
            "XRPUSDT": "XRP"
        }

        self.cache = None
        self.cached_at = 0
        self.cache_duration = 60

        self.lock = threading.Lock()

    def fetch_ticker(self, symbol):
        """Fetch 24-hour statistics for one cryptocurrency."""

        try:
            response = requests.get(
                self.url,
                params={"symbol": symbol},
                timeout=10
            )

            if not response.ok:
                raise RuntimeError(
                    f"Binance error for {symbol}: "
                    f"HTTP {response.status_code} - "
                    f"{response.text[:300]}"
                )

            data = response.json()

            if not isinstance(data, dict):
                raise ValueError(
                    f"Invalid ticker response for {symbol}"
                )

            return {
                "symbol": symbol.replace("USDT", ""),
                "name": self.asset_names.get(symbol, symbol),
                "pair": symbol,
                "price": float(data["lastPrice"]),
                "change": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["quoteVolume"]),
                "trades": int(data["count"])
            }

        except requests.RequestException as e:
            raise RuntimeError(
                f"Network request failed for {symbol}: {e}"
            ) from e

    def get_markets(self):
        """Get market data with 60-second caching."""

        with self.lock:

            now = time.time()

            if (
                self.cache is not None
                and now - self.cached_at < self.cache_duration
            ):
                return self.cache

            try:
                markets = []

                for symbol in self.symbols:
                    ticker = self.fetch_ticker(symbol)
                    markets.append(ticker)

                result = {
                    "markets": markets,
                    "updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "stale": False
                }

                self.cache = result
                self.cached_at = time.time()

                print(
                    f"Successfully fetched {len(markets)} markets"
                )

                return result

            except Exception as e:

                print("Market API error:", e)

                if self.cache is not None:
                    return {
                        **self.cache,
                        "stale": True
                    }

                raise RuntimeError(
                    f"Live market data unavailable: {e}"
                ) from e
