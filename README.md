# CryptoScope

Cryptocurrency market data pipeline built with Python (OOP).
It collects one year of hourly candles from the Binance public API for
BTC, ETH, SOL, BNB and XRP, cleans and validates them, and will store
them in SQLite for analysis.

## Status

- [x] Extract: Binance client, pagination, raw JSON cache
- [x] Transform: raw candles to typed Pandas DataFrame
- [x] Validate: Pydantic row checks, duplicate and missing-hour detection
- [ ] Load: SQLite database
- [ ] Analysis and charts

## Setup

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

## Run

    python run.py