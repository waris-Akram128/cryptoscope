
import os
import json
import time

from cryptoscope.config import CryptoScopeConfig
from cryptoscope.extract.binance_client import BinanceClient


class RawExtractor:
    def __init__(self):
        self.client = BinanceClient()

    def run(self):
        """Return {symbol: raw candles}.

        Load cached JSON files when available.
        Raise an error if extraction fails.
        """

        print("STAGE 1: EXTRACT")

        raw_data = {}

        try:
            os.makedirs(
                CryptoScopeConfig.RAW_FOLDER,
                exist_ok=True
            )

            for symbol in CryptoScopeConfig.SYMBOLS:

                try:
                    file_name = (
                        f"{symbol}_{CryptoScopeConfig.INTERVAL}.json"
                    )

                    path = os.path.join(
                        CryptoScopeConfig.RAW_FOLDER,
                        file_name
                    )

                    # 1. Load existing JSON data
                    if os.path.exists(path):

                        with open(path, "r", encoding="utf-8") as f:
                            candles = json.load(f)

                        print(
                            f"  {symbol}: loaded from file "
                            f"({len(candles)} candles)"
                        )

                    # 2. Download data if file doesn't exist
                    else:
                        print(f"  {symbol}: downloading...")

                        candles = self.client.get_historical_klines(
                            symbol,
                            CryptoScopeConfig.INTERVAL,
                            CryptoScopeConfig.DAYS
                        )

                        # Check downloaded data
                        if not isinstance(candles, list):
                            raise ValueError(
                                "Binance returned an invalid response"
                            )

                        if len(candles) == 0:
                            raise ValueError(
                                "Binance returned no candles"
                            )

                        expected = (
                            CryptoScopeConfig.DAYS * 24
                        )

                        if len(candles) == expected:

                            with open(
                                path, "w", encoding="utf-8"
                            ) as f:
                                json.dump(candles, f)

                            print(
                                f"  {symbol}: saved "
                                f"({len(candles)} candles)"
                            )

                        else:
                            print(
                                f"  {symbol}: WARNING "
                                f"got {len(candles)}, "
                                f"expected {expected}"
                            )

                        time.sleep(1)

                    # 3. Validate cached or downloaded data
                    if not isinstance(candles, list):
                        raise ValueError(
                            "Candle data must be a list"
                        )

                    if len(candles) == 0:
                        raise ValueError(
                            "Candle dataset is empty"
                        )

                    # 4. Store data in dictionary
                    raw_data[symbol] = candles

                except Exception as e:
                    raise RuntimeError(
                        f"Extraction failed for {symbol}: {e}"
                    ) from e

            return raw_data

        except Exception as e:
            raise RuntimeError(
                f"Extract stage failed: {e}"
            ) from e
