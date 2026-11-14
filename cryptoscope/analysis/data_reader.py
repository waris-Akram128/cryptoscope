
import pandas as pd

from cryptoscope.load.database import DatabaseManager
from cryptoscope.config import CryptoScopeConfig


class CandleDataReader:
    def __init__(self):
        self.db = DatabaseManager()

    def get_candles(self, symbol=None, start=None, end=None):
        """
        Read historical candles from SQLite.

        symbol: e.g. BTCUSDT, or None for all assets
        start: optional starting date/time
        end: optional ending date/time

        Returns a Pandas DataFrame.
        """

        if symbol is not None:
            if symbol not in CryptoScopeConfig.SYMBOLS:
                raise ValueError(f"Unknown symbol: {symbol}")

        query = """
            SELECT
                a.symbol,
                c.open_time,
                c.open,
                c.high,
                c.low,
                c.close,
                c.volume,
                c.quote_volume,
                c.trades
            FROM fact_candles_1h AS c
            JOIN dim_asset AS a
                ON c.asset_id = a.asset_id
            WHERE 1 = 1
        """

        params = []

        if symbol is not None:
            query += " AND a.symbol = ?"
            params.append(symbol)

        if start is not None:
            start = pd.to_datetime(start, utc=True)
            query += " AND c.open_time >= ?"
            params.append(start.strftime("%Y-%m-%d %H:%M:%S"))

        if end is not None:
            end = pd.to_datetime(end, utc=True)
            query += " AND c.open_time <= ?"
            params.append(end.strftime("%Y-%m-%d %H:%M:%S"))

        query += " ORDER BY c.open_time ASC, a.symbol ASC"

        conn = self.db.get_connection()

        if conn is None:
            raise RuntimeError("Cannot connect to SQLite database")

        try:
            df = pd.read_sql_query(
                query,
                conn,
                params=params
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to read candle data: {e}"
            ) from e

        finally:
            conn.close()

        # Convert timestamps into timezone-aware datetimes
        df["open_time"] = pd.to_datetime(
            df["open_time"],
            utc=True
        )

        return df
