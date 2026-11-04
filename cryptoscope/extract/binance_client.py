import requests
import time
# Milliseconds in one candle. This sits at the TOP of the file,
# at the left margin, outside the class.
INTERVAL_MS = {
    "1m": 60000,
    "5m": 300000,
    "15m": 900000,
    "1h": 3600000,
    "4h": 14400000,
    "1d": 86400000,
}


class BinanceClient:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()

    # to get candels 
    def get_klines(self, symbol, interval="1h", limit=1000, start_time=None, end_time=None):
        """Fetch ONE batch of candles. Returns a list, or None on error."""
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        try:
            url = self.base_url + "/api/v3/klines"
            response = self.session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            print("Error: request timed out")
        except requests.exceptions.HTTPError as e:
            print("Error: Binance returned a bad status:", e)
        except requests.exceptions.RequestException as e:
            print("Error: network problem:", e)
        except ValueError:
            print("Error: response was not valid JSON")
        return None
    def get_historical_klines(self, symbol, interval="1h", days=365):
        """Fetch the last `days` days of CLOSED candles."""
        try:
            step = INTERVAL_MS[interval]
            total = (days * 86400000) // step

            # Round down to the start of the current (open) candle,
            # then go back one candle to get the last CLOSED one
            now_ms = int(time.time() * 1000)
            last_open = (now_ms // step) * step - step

            # Step back to the first candle we want
            next_start = last_open - (total - 1) * step

            all_candles = []

            while len(all_candles) < total:
                batch_size = min(1000, total - len(all_candles))

                batch = self.get_klines(
                    symbol, interval,
                    limit=batch_size,
                    start_time=next_start,
                )

                if not batch:      # None (error) or empty (no more data)
                    break

                all_candles.extend(batch)
                next_start = batch[-1][0] + step

            return all_candles

        except KeyError:
            print("Error: unsupported interval:", interval)
            return []  