"""
Fibrios market data layer.

Swap the provider by changing DATA_PROVIDER env var or calling get_provider().
Currently supported: "tradingview" (default)
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List


SUPPORTED_SYMBOLS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "NAS100", "SPX500"]

# Maps Fibrios symbol → (tvdatafeed symbol, exchange)
_TV_SYMBOL_MAP: Dict[str, tuple] = {
    "XAUUSD": ("XAUUSD", "OANDA"),
    "XAGUSD": ("XAGUSD", "OANDA"),
    "EURUSD": ("EURUSD", "FX"),
    "GBPUSD": ("GBPUSD", "FX"),
    "USDJPY": ("USDJPY", "FX"),
    "NAS100": ("NAS100", "OANDA"),
    "SPX500": ("SPX500", "OANDA"),
}

_TIMEFRAME_LABELS = ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"]


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


class TradingViewProvider(MarketDataProvider):
    """
    TradingView data provider via tvdatafeed.

    Install:  pip install tvdatafeed
    No broker connection or API key required.
    """

    def __init__(self) -> None:
        try:
            from tvdatafeed import TvDatafeed, Interval  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "tvdatafeed is required for the TradingView provider.\n"
                "Install it with: pip install tvdatafeed"
            ) from exc

        self._tv = TvDatafeed()
        self._Interval = Interval

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_symbol(self, symbol: str) -> tuple:
        if symbol not in _TV_SYMBOL_MAP:
            raise ValueError(
                f"Unsupported symbol '{symbol}'. Supported: {SUPPORTED_SYMBOLS}"
            )
        return _TV_SYMBOL_MAP[symbol]

    def _map_interval(self, timeframe: str):
        mapping = {
            "1m":  self._Interval.in_1_minute,
            "5m":  self._Interval.in_5_minute,
            "15m": self._Interval.in_15_minute,
            "30m": self._Interval.in_30_minute,
            "1h":  self._Interval.in_1_hour,
            "4h":  self._Interval.in_4_hour,
            "1D":  self._Interval.in_daily,
            "1W":  self._Interval.in_weekly,
        }
        if timeframe not in mapping:
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. Supported: {_TIMEFRAME_LABELS}"
            )
        return mapping[timeframe]

    def _df_to_candles(self, df) -> List[Dict[str, Any]]:
        candles: List[Dict[str, Any]] = []
        for ts, row in df.iterrows():
            candles.append(
                {
                    "time": str(ts),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0)),
                }
            )
        return candles

    # ------------------------------------------------------------------
    # MarketDataProvider interface
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> Dict[str, Any]:
        candles = self.get_latest_candles(symbol, "1m", count=1)
        if not candles:
            raise ValueError(f"No price data returned for {symbol}")
        last = candles[-1]
        return {
            "symbol": symbol,
            "price": last["close"],
            "open": last["open"],
            "high": last["high"],
            "low": last["low"],
            "time": last["time"],
        }

    def get_ohlc(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        candles = self.get_latest_candles(symbol, timeframe, count=1)
        if not candles:
            raise ValueError(f"No OHLC data for {symbol}/{timeframe}")
        return candles[-1]

    def get_latest_candles(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> List[Dict[str, Any]]:
        tv_symbol, exchange = self._resolve_symbol(symbol)
        interval = self._map_interval(timeframe)
        df = self._tv.get_hist(
            symbol=tv_symbol,
            exchange=exchange,
            interval=interval,
            n_bars=count,
        )
        if df is None or df.empty:
            raise ValueError(f"TradingView returned no data for {symbol}/{timeframe}")
        return self._df_to_candles(df)

    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        tv_symbol, exchange = self._resolve_symbol(symbol)
        return {
            "symbol": symbol,
            "tv_symbol": tv_symbol,
            "exchange": exchange,
            "supported_timeframes": _TIMEFRAME_LABELS,
        }


def get_provider(name: str | None = None) -> MarketDataProvider:
    """
    Factory — returns the configured MarketDataProvider.

    Override by setting DATA_PROVIDER env var (default: "tradingview").
    """
    name = name or os.getenv("DATA_PROVIDER", "tradingview")
    if name == "tradingview":
        return TradingViewProvider()
    raise ValueError(
        f"Unknown data provider '{name}'. "
        "Implement MarketDataProvider and register it here."
    )
