"""
Fibrios market data layer.

Data source: Yahoo Finance via yfinance (TradingView charts shown in UI).
Swap the provider by changing DATA_PROVIDER env var or calling get_provider().
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


SUPPORTED_SYMBOLS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "NAS100", "SPX500"]

# Maps Fibrios symbol -> Yahoo Finance ticker
_YF_SYMBOL_MAP: Dict[str, str] = {
    "XAUUSD": "GC=F",       # Gold futures
    "XAGUSD": "SI=F",       # Silver futures
    "EURUSD": "EURUSD=X",   # EUR/USD forex
    "GBPUSD": "GBPUSD=X",   # GBP/USD forex
    "USDJPY": "USDJPY=X",   # USD/JPY forex
    "NAS100": "^NDX",       # NASDAQ 100 index (matches TradingView NAS100)
    "SPX500": "^GSPC",      # S&P 500 index (matches TradingView SPX500)
}

# Maps Fibrios timeframe -> yfinance interval
_YF_INTERVAL_MAP: Dict[str, str] = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "4h":  "1h",   # yfinance has no 4h; use 1h and group
    "1D":  "1d",
    "1W":  "1wk",
}

# yfinance period needed to get enough bars per timeframe
_YF_PERIOD_MAP: Dict[str, str] = {
    "1m":  "1d",
    "5m":  "5d",
    "15m": "5d",
    "30m": "1mo",
    "1h":  "1mo",
    "4h":  "3mo",
    "1D":  "6mo",
    "1W":  "2y",
}

_TIMEFRAME_LABELS = list(_YF_INTERVAL_MAP.keys())


class MarketDataProvider(ABC):
    """Abstract interface for all Fibrios market data providers."""

    @abstractmethod
    def get_price(self, symbol: str) -> Dict[str, Any]:
        """Return current price snapshot: symbol, price, open, high, low, time."""

    @abstractmethod
    def get_ohlc(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Return the most recent completed OHLC candle."""

    @abstractmethod
    def get_latest_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> List[Dict[str, Any]]:
        """Return the latest *count* OHLC candles as a list of dicts."""

    @abstractmethod
    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """Return symbol metadata: name, exchange, supported timeframes."""


class YFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance data provider via yfinance.

    Install: pip install yfinance
    No API key required. TradingView charts are still shown in the UI.
    """

    def __init__(self) -> None:
        try:
            import yfinance  # type: ignore
            self._yf = yfinance
        except ImportError as exc:
            raise ImportError(
                "yfinance is required.\n"
                "Install it with: python -m pip install yfinance"
            ) from exc

    def _ticker(self, symbol: str) -> str:
        if symbol not in _YF_SYMBOL_MAP:
            raise ValueError(
                f"Unsupported symbol '{symbol}'. Supported: {SUPPORTED_SYMBOLS}"
            )
        return _YF_SYMBOL_MAP[symbol]

    def _df_to_candles(self, df, count: int) -> List[Dict[str, Any]]:
        df = df.tail(count)
        candles: List[Dict[str, Any]] = []
        for ts, row in df.iterrows():
            candles.append({
                "time": str(ts),
                "open":   float(row["Open"]),
                "high":   float(row["High"]),
                "low":    float(row["Low"]),
                "close":  float(row["Close"]),
                "volume": float(row.get("Volume", 0)),
            })
        return candles

    def get_price(self, symbol: str) -> Dict[str, Any]:
        candles = self.get_latest_candles(symbol, "1D", count=1)
        if not candles:
            raise ValueError(f"No price data for {symbol}")
        last = candles[-1]
        return {
            "symbol": symbol,
            "price":  last["close"],
            "open":   last["open"],
            "high":   last["high"],
            "low":    last["low"],
            "time":   last["time"],
        }

    def get_ohlc(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        candles = self.get_latest_candles(symbol, timeframe, count=1)
        if not candles:
            raise ValueError(f"No OHLC data for {symbol}/{timeframe}")
        return candles[-1]

    def get_latest_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> List[Dict[str, Any]]:
        ticker = self._ticker(symbol)
        interval = _YF_INTERVAL_MAP.get(timeframe, "1d")
        period = _YF_PERIOD_MAP.get(timeframe, "1mo")
        df = self._yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            raise ValueError(f"No data returned for {symbol}/{timeframe}")
        # Flatten multi-level columns if present
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)
        return self._df_to_candles(df, count)

    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "yf_ticker": self._ticker(symbol),
            "supported_timeframes": _TIMEFRAME_LABELS,
        }


def get_provider(name: Optional[str] = None) -> MarketDataProvider:
    """
    Factory — returns the configured MarketDataProvider.

    Override by setting DATA_PROVIDER env var (default: "yfinance").
    """
    name = name or os.getenv("DATA_PROVIDER", "yfinance")
    if name in ("yfinance", "tradingview"):
        return YFinanceProvider()
    raise ValueError(
        f"Unknown data provider '{name}'. "
        "Implement MarketDataProvider and register it here."
    )
