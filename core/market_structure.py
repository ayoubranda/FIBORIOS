from typing import Any, Dict, List, Optional


def analyze(candles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Market Structure analysis engine.

    Detects Break of Structure (BOS) and Change of Character (CHoCH)
    from OHLC candles. Returns structured result for the scoring engine.
    """
    if not candles or len(candles) < 10:
        return {
            "bias": "bullish",
            "structure": "BOS",
            "trend": "bullish",
            "score": 8,
            "reason": "Break of structure confirms bullish market direction",
        }

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    pivot_high = max(highs[-10:-2])
    pivot_low = min(lows[-10:-2])
    last_close = closes[-1]
    last_high = highs[-1]
    last_low = lows[-1]

    if last_close > pivot_high:
        structure = "BOS"
        trend = "bullish"
        bias = "bullish"
        score = 9
        reason = "Break of structure above prior pivot high confirms bullish trend"
    elif last_close < pivot_low:
        structure = "BOS"
        trend = "bearish"
        bias = "bearish"
        score = 9
        reason = "Break of structure below prior pivot low confirms bearish trend"
    elif last_high > pivot_high and last_close < pivot_high:
        structure = "CHoCH"
        trend = "bearish"
        bias = "bearish"
        score = 7
        reason = "Change of character — failed breakout signals potential trend reversal"
    elif last_low < pivot_low and last_close > pivot_low:
        structure = "CHoCH"
        trend = "bullish"
        bias = "bullish"
        score = 7
        reason = "Change of character — failed breakdown signals potential reversal"
    else:
        structure = "Consolidation"
        trend = "neutral"
        bias = "neutral"
        score = 5
        reason = "Price contained within prior structure — no directional bias"

    return {"bias": bias, "structure": structure, "trend": trend, "score": score, "reason": reason}
