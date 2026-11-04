import json
import os
import pandas as pd
from cryptoscope.transform.data_transformer import DataTransformer
from cryptoscope.validate.candle_validator import CandleValidator


def show_result(name, passed):
    if passed:
        print("PASS -", name)
    else:
        print("FAIL -", name)


try:
    # Load 100 real candles from the saved raw file
    with open(os.path.join("data", "raw", "BTCUSDT_1h.json"), "r") as f:
        candles = json.load(f)

    transformer = DataTransformer()
    validator = CandleValidator()

    # ---------- TEST 1: clean data ----------
    print("TEST 1: clean data")
    df = transformer.transform(candles[:100], "BTCUSDT")
    clean, rejected, report = validator.validate(df, "BTCUSDT")
    print(report)

    show_result("no duplicates", report["duplicates_removed"] == 0)
    show_result("no rejected rows", report["rows_rejected"] == 0)
    show_result("no missing hours", report["missing_hours"] == 0)
    show_result("all 100 rows kept", report["rows_clean"] == 100)

    # ---------- TEST 2: broken data ----------
    print()
    print("TEST 2: broken data")
    df = transformer.transform(candles[:100], "BTCUSDT")

    df.loc[10, "high"] = df.loc[10, "low"] - 1     # high below low
    df = df.drop(index=20)                          # remove one hour
    df = pd.concat([df, df.iloc[[30]]])             # add one duplicate

    clean, rejected, report = validator.validate(df, "BTCUSDT")
    print(report)
    print()
    print(rejected[["open_time", "reason"]])
    print()

    show_result("1 duplicate removed", report["duplicates_removed"] == 1)
    show_result("1 row rejected", report["rows_rejected"] == 1)
    show_result("2 missing hours", report["missing_hours"] == 2)
    show_result("98 rows kept", report["rows_clean"] == 98)

except Exception as e:
    print("Test failed:", e)