
import csv
import io
import math
from datetime import datetime, timedelta, timezone

from cryptoscope.config import CryptoScopeConfig
from cryptoscope.load.database import DatabaseManager


class DataService:

    def __init__(self):
        self.db = DatabaseManager()
        self.symbols = set(CryptoScopeConfig.SYMBOLS)
        self.allowed_page_sizes = {25, 50, 100}
        self.max_export_rows = 20000

        self.columns = [
            "symbol",
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "trades"
        ]

    def validate_filters(
        self,
        symbol=None,
        start=None,
        end=None
    ):
        """Validate filters and build SQL conditions."""

        if symbol and symbol not in self.symbols:
            raise ValueError("Unsupported cryptocurrency")

        conditions = []
        params = []

        if symbol:
            conditions.append("a.symbol = ?")
            params.append(symbol)

        start_date = None
        end_date = None

        if start:
            try:
                start_date = datetime.strptime(
                    start, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError(
                    "Start date must use YYYY-MM-DD"
                )

            conditions.append("c.open_time >= ?")
            params.append(
                start_date.strftime("%Y-%m-%d %H:%M:%S")
            )

        if end:
            try:
                end_date = datetime.strptime(
                    end, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError(
                    "End date must use YYYY-MM-DD"
                )

            # End date is inclusive.
            next_day = end_date + timedelta(days=1)

            conditions.append("c.open_time < ?")
            params.append(
                next_day.strftime("%Y-%m-%d %H:%M:%S")
            )

        if start_date and end_date:
            if start_date > end_date:
                raise ValueError(
                    "Start date cannot be after end date"
                )

        where = " AND ".join(conditions)

        if where:
            where = "WHERE " + where

        return where, params

    def base_query(self):
        return """
            FROM fact_candles_1h AS c
            JOIN dim_asset AS a
                ON c.asset_id = a.asset_id
        """

    def get_records(
        self,
        symbol=None,
        start=None,
        end=None,
        page=1,
        page_size=25
    ):
        """Return a single page of candle records."""

        if page < 1:
            raise ValueError("Page must be at least 1")

        if page_size not in self.allowed_page_sizes:
            raise ValueError(
                "Page size must be 25, 50 or 100"
            )

        where, params = self.validate_filters(
            symbol, start, end
        )

        conn = self.db.get_connection()

        if conn is None:
            raise RuntimeError(
                "Cannot connect to SQLite"
            )

        try:
            # Total matching records
            count_query = (
                "SELECT COUNT(*) "
                + self.base_query()
                + where
            )

            total = conn.execute(
                count_query, params
            ).fetchone()[0]

            total_pages = max(
                1, math.ceil(total / page_size)
            )

            page = min(page, total_pages)

            offset = (page - 1) * page_size

            query = f"""
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
                {self.base_query()}
                {where}
                ORDER BY c.open_time DESC, a.symbol ASC
                LIMIT ? OFFSET ?
            """

            cursor = conn.execute(
                query,
                params + [page_size, offset]
            )

            records = [
                dict(zip(self.columns, row))
                for row in cursor.fetchall()
            ]

            # Filtered dataset summary
            summary_query = f"""
                SELECT
                    COUNT(*),
                    MIN(c.open_time),
                    MAX(c.open_time),
                    COUNT(DISTINCT a.symbol)
                {self.base_query()}
                {where}
            """

            summary = conn.execute(
                summary_query, params
            ).fetchone()

            return {
                "records": records,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_records": total,
                    "total_pages": total_pages
                },
                "summary": {
                    "total_candles": summary[0],
                    "earliest": summary[1],
                    "latest": summary[2],
                    "assets": summary[3]
                },
                "source": "CryptoScope SQLite"
            }

        except Exception as e:
            raise RuntimeError(
                f"Data Explorer query failed: {e}"
            ) from e

        finally:
            conn.close()

    def export_csv(
        self,
        symbol=None,
        start=None,
        end=None
    ):
        """Export up to 20,000 filtered records as CSV."""

        where, params = self.validate_filters(
            symbol, start, end
        )

        conn = self.db.get_connection()

        if conn is None:
            raise RuntimeError(
                "Cannot connect to SQLite"
            )

        try:
            count_query = (
                "SELECT COUNT(*) "
                + self.base_query()
                + where
            )

            total = conn.execute(
                count_query, params
            ).fetchone()[0]

            if total > self.max_export_rows:
                raise ValueError(
                    f"Export contains {total:,} records. "
                    f"Maximum is {self.max_export_rows:,}. "
                    "Choose a coin or a shorter date range."
                )

            query = f"""
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
                {self.base_query()}
                {where}
                ORDER BY c.open_time ASC, a.symbol ASC
            """

            output = io.StringIO(newline="")

            writer = csv.writer(output)
            writer.writerow(self.columns)

            cursor = conn.execute(query, params)

            for row in cursor:
                writer.writerow(row)

            return output.getvalue()

        finally:
            conn.close()
