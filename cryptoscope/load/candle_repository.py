from cryptoscope.config import CryptoScopeConfig
from cryptoscope.load.database import DatabaseManager

INSERT_CANDLE = """
INSERT OR IGNORE INTO fact_candles_1h
    (asset_id, open_time, open, high, low, close, volume, quote_volume, trades)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class CandleRepository:
    def __init__(self):
        self.db = DatabaseManager()

    def save_candles(self, df, symbol):
        """Save one coin's clean candles. Return (inserted, ignored), or None on error."""
        conn = self.db.get_connection()
        if conn is None:
            return None

        try:
            # 1. Register the coin (does nothing if it already exists)
            name = CryptoScopeConfig.ASSET_NAMES.get(symbol, symbol)
            conn.execute(
                "INSERT OR IGNORE INTO dim_asset (symbol, name) VALUES (?, ?)",
                (symbol, name),
            )
            row = conn.execute(
                "SELECT asset_id FROM dim_asset WHERE symbol = ?", (symbol,)
            ).fetchone()
            asset_id = row[0]

            # 2. Turn the DataFrame into a list of tuples
            rows = []
            for r in df.itertuples(index=False):
                rows.append((
                    asset_id,
                    r.open_time.strftime("%Y-%m-%d %H:%M:%S"),
                    float(r.open), float(r.high), float(r.low), float(r.close),
                    float(r.volume), float(r.quote_volume), int(r.trades),
                ))

            # 3. Insert everything; the database skips duplicates
            before = conn.total_changes
            conn.executemany(INSERT_CANDLE, rows)
            inserted = conn.total_changes - before

            conn.commit()
            return inserted, len(rows) - inserted

        except Exception as e:
            conn.rollback()
            print("Save candles error for", symbol, ":", e)
            return None

        finally:
            conn.close()

    def count_candles(self, symbol=None):
        """Count stored candles (all coins, or one coin). Return None on error."""
        conn = self.db.get_connection()
        if conn is None:
            return None

        try:
            if symbol is None:
                row = conn.execute("SELECT COUNT(*) FROM fact_candles_1h").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM fact_candles_1h c "
                    "JOIN dim_asset a ON a.asset_id = c.asset_id "
                    "WHERE a.symbol = ?",
                    (symbol,),
                ).fetchone()
            return row[0]

        except Exception as e:
            print("Count candles error:", e)
            return None

        finally:
            conn.close()