
import os
import json
import time

from cryptoscope.config import CryptoScopeConfig
from cryptoscope.extract.binance_client import BinanceClient
from cryptoscope.load.candle_repository import CandleRepository


class RawExtractor:
    def __init__(self):
        self.client = BinanceClient()
        self.repository = CandleRepository()

    def load_cache(self, path):
        """Load cached raw candles from JSON."""

        if not os.path.exists(path):
            return []

        with open(path, "r", encoding="utf-8") as f:
            candles = json.load(f)

        if not isinstance(candles, list):
            raise ValueError("Invalid JSON cache format")

        return candles

    def save_cache(self, path, candles):
        """Save candles using an atomic file replacement."""

        temp_path = path + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(candles, f)

            os.replace(temp_path, path)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def merge_candles(self, old_candles, new_candles):
        """Merge candles using opening time as unique key."""

        merged = {}

        for candle in old_candles + new_candles:
            if not isinstance(candle, list) or not candle:
                raise ValueError("Invalid candle in raw data")

            open_time = int(candle[0])
            merged[open_time] = candle

        return [
            merged[key]
            for key in sorted(merged)
        ]

    def run(self):
        """Extract historical or incremental candles."""

        print("STAGE 1: EXTRACT")

        os.makedirs(
            CryptoScopeConfig.RAW_FOLDER,
            exist_ok=True
        )

        raw_data = {}

        for symbol in CryptoScopeConfig.SYMBOLS:

            try:
                file_name = (
                    f"{symbol}_{CryptoScopeConfig.INTERVAL}.json"
                )

                path = os.path.join(
                    CryptoScopeConfig.RAW_FOLDER,
                    file_name
                )

                # 1. Check the latest candle in SQLite
                latest = self.repository.get_latest_candle_time(
                    symbol
                )

                # 2. First run: historical extraction
                if latest is None:

                    print(
                        f"  {symbol}: no database history, "
                        "downloading historical data..."
                    )

                    candles = self.client.get_historical_klines(
                        symbol,
                        CryptoScopeConfig.INTERVAL,
                        CryptoScopeConfig.DAYS
                    )

                    if not isinstance(candles, list) or not candles:
                        raise RuntimeError(
                            "Historical download returned no candles"
                        )

                    candles = self.merge_candles([], candles)

                    self.save_cache(path, candles)

                    print(
                        f"  {symbol}: downloaded "
                        f"{len(candles)} historical candles"
                    )

                # 3. Existing history: incremental extraction
                else:

                    print(
                        f"  {symbol}: latest stored candle = {latest}"
                    )

                    new_candles = self.client.get_new_klines(
                        symbol,
                        latest,
                        CryptoScopeConfig.INTERVAL
                    )

                    if not isinstance(new_candles, list):
                        raise RuntimeError(
                            "Incremental download failed"
                        )

                    old_candles = self.load_cache(path)

                    candles = self.merge_candles(
                        old_candles,
                        new_candles
                    )

                    if not candles:
                        raise RuntimeError(
                            "No cached or new candle data available"
                        )

                    if new_candles:
                        self.save_cache(path, candles)

                    print(
                        f"  {symbol}: "
                        f"{len(new_candles)} downloaded, "
                        f"{len(candles)} total cached candles"
                    )

                raw_data[symbol] = candles

                time.sleep(0.2)

            except Exception as e:
                raise RuntimeError(
                    f"Extraction failed for {symbol}: {e}"
                ) from e

        return raw_data
