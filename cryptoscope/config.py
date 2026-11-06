import os


class CryptoScopeConfig:
    API_URL = "https://api.binance.com"
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    INTERVAL = "1h"
    DAYS = 365
    ASSET_NAMES = {
        "BTCUSDT": "Bitcoin",
        "ETHUSDT": "Ethereum",
        "SOLUSDT": "Solana",
        "BNBUSDT": "BNB",
        "XRPUSDT": "XRP",
    }

    DATA_FOLDER = "data"
    RAW_FOLDER = os.path.join("data", "raw")
    DATABASE_PATH = os.path.join("data", "cryptoscope.db")