from datetime import datetime
from pydantic import BaseModel, model_validator


class CandleModel(BaseModel):
    symbol: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int

    @model_validator(mode="after")
    def check_candle(self):
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("price must be above 0")
        if self.high < self.low:
            raise ValueError("high is lower than low")
        if self.high < max(self.open, self.close):
            raise ValueError("high is below open or close")
        if self.low > min(self.open, self.close):
            raise ValueError("low is above open or close")
        if self.volume < 0 or self.quote_volume < 0 or self.trades < 0:
            raise ValueError("volume or trades is negative")
        return self