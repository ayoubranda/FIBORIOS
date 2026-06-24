from typing import Any, Dict, List, Optional


def analyze(candles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Liquidity analysis engine.

    Accepts OHLC candles from the data layer. Detects buy/sell-side sweeps
    and liquidity grabs. Returns structured result for the scoring engine.
    """
    if not candles or len(candles) < 10:
        return {
            "sweep": "Buy Side Liquidity Taken",
            "bias": "bullish",
            "score": 8,
            "reason": "Liquidity sweep followed by bullish displacement",
        }

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    recent_high = max(highs[-3:])
    prior_swing_high = max(highs[-10:-3])
    recent_low = min(lows[-3:])
    prior_swing_low = min(lows[-10:-3])

    buy_side_sweep = recent_high > prior_swing_high and closes[-1] < recent_high
    sell_side_sweep = recent_low < prior_swing_low and closes[-1] > recent_low

    if buy_side_sweep and closes[-1] < closes[-2]:
        sweep = "Buy Side Liquidity Swept"
        bias = "bearish"
        score = 8
        reason = "Price swept buy-side liquidity then reversed — bearish displacement"
    elif sell_side_sweep and closes[-1] > closes[-2]:
        sweep = "Sell Side Liquidity Swept"
        bias = "bullish"
        score = 8
        reason = "Price swept sell-side liquidity then reversed — bullish displacement"
    elif closes[-1] > closes[-5]:
        sweep = "No Sweep Detected"
        bias = "bullish"
        score = 6
        reason = "Bullish momentum without a liquidity sweep"
    else:
        sweep = "No Sweep Detected"
        bias = "bearish"
        score = 6
        reason = "Bearish momentum without a liquidity sweep"

    return {"sweep": sweep, "bias": bias, "score": score, "reason": reason}
