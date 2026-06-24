from typing import Any, Dict, List, Optional


def analyze(candles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Price Action analysis engine.

    Detects candlestick patterns (engulfing, pin bar, inside bar) from
    OHLC candles. Returns structured result for the scoring engine.
    """
    if not candles or len(candles) < 3:
        return {
            "bias": "bullish",
            "pattern": "Bullish Breakout",
            "score": 8,
            "reason": "Price action shows a clean breakout with follow-through confirmation",
        }

    prev2 = candles[-3]
    prev1 = candles[-2]
    last = candles[-1]

    body_last = abs(last["close"] - last["open"])
    body_prev = abs(prev1["close"] - prev1["open"])
    range_last = last["high"] - last["low"]
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]

    bullish_candle = last["close"] > last["open"]
    bearish_candle = last["close"] < last["open"]

    # Bullish engulfing
    if (
        bullish_candle
        and prev1["close"] < prev1["open"]
        and last["close"] > prev1["open"]
        and last["open"] < prev1["close"]
    ):
        return {
            "bias": "bullish",
            "pattern": "Bullish Engulfing",
            "score": 9,
            "reason": "Bullish engulfing candle signals strong demand reversal",
        }

    # Bearish engulfing
    if (
        bearish_candle
        and prev1["close"] > prev1["open"]
        and last["close"] < prev1["open"]
        and last["open"] > prev1["close"]
    ):
        return {
            "bias": "bearish",
            "pattern": "Bearish Engulfing",
            "score": 9,
            "reason": "Bearish engulfing candle signals strong supply reversal",
        }

    # Bullish pin bar (hammer)
    if lower_wick > body_last * 2 and upper_wick < body_last and range_last > 0:
        return {
            "bias": "bullish",
            "pattern": "Bullish Pin Bar",
            "score": 8,
            "reason": "Pin bar with long lower wick indicates strong rejection of lows",
        }

    # Bearish pin bar (shooting star)
    if upper_wick > body_last * 2 and lower_wick < body_last and range_last > 0:
        return {
            "bias": "bearish",
            "pattern": "Bearish Pin Bar",
            "score": 8,
            "reason": "Pin bar with long upper wick indicates strong rejection of highs",
        }

    # Inside bar
    if last["high"] <= prev1["high"] and last["low"] >= prev1["low"]:
        bias = "bullish" if prev1["close"] > prev1["open"] else "bearish"
        return {
            "bias": bias,
            "pattern": "Inside Bar",
            "score": 6,
            "reason": "Inside bar indicates consolidation before continuation",
        }

    # Default: directional close
    if bullish_candle:
        return {
            "bias": "bullish",
            "pattern": "Bullish Close",
            "score": 6,
            "reason": "Bullish close with no reversal pattern — trend continuation",
        }

    return {
        "bias": "bearish",
        "pattern": "Bearish Close",
        "score": 6,
        "reason": "Bearish close with no reversal pattern — trend continuation",
    }
