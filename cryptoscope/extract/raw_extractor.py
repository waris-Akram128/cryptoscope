import os
import json
import time
from cryptoscope.config import CryptoScopeConfig
from cryptoscope.extract.binance_client import BinanceClient


class RawExtractor:
    def __init__(self):
        self.client = BinanceClient()

    def run(self):
        """Return {symbol: raw candles}. Uses saved files when they exist."""
        raw_data = {}

        try:
            os.makedirs(CryptoScopeConfig.RAW_FOLDER, exist_ok=True)

            for symbol in CryptoScopeConfig.SYMBOLS:
                file_name = f"{symbol}_{CryptoScopeConfig.INTERVAL}.json"
                path = os.path.join(CryptoScopeConfig.RAW_FOLDER, file_name)

                if os.path.exists(path):
                    with open(path, "r") as f:
                        candles = json.load(f)
                    print(f"  {symbol}: loaded from file ({len(candles)})")
                else:
                    print(f"  {symbol}: downloading...")
                    candles = self.client.get_historical_klines(
                        symbol, CryptoScopeConfig.INTERVAL, CryptoScopeConfig.DAYS
                    )
                    expected = CryptoScopeConfig.DAYS * 24

                    if len(candles) == expected:
                        with open(path, "w") as f:
                            json.dump(candles, f)
                        print(f"  {symbol}: saved ({len(candles)})")
                    else:
                        print(f"  {symbol}: WARNING got {len(candles)}, expected {expected}")

                    time.sleep(1)

                raw_data[symbol] = candles

        except Exception as e:
            print("Extract stage failed:", e)

        return raw_data