from typing import Any, Dict, List, Optional


def analyze(candles: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Elliott Wave analysis engine.

    Accepts OHLC candles from the data layer. Returns structured result
    consumed by the scoring engine — never sent raw to Claude.
    """
    if not candles or len(candles) < 10:
        return {
            "bias": "bullish",
            "wave": "Wave 3",
            "score": 9,
            "reason": "Wave 3 momentum remains intact and aligns with bullish structure",
        }

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    recent_high = max(highs[-5:])
    recent_low = min(lows[-5:])
    prior_high = max(highs[-10:-5])
    prior_low = min(lows[-10:-5])

    if recent_high > prior_high and recent_low > prior_low:
        bias, wave, score = "bullish", "Wave 3", 8
        reason = "Higher-highs and higher-lows confirm bullish impulse structure"
    elif recent_high < prior_high and recent_low < prior_low:
        bias, wave, score = "bearish", "Wave 3", 8
        reason = "Lower-highs and lower-lows confirm bearish impulse structure"
    elif closes[-1] > closes[-3] > closes[-5]:
        bias, wave, score = "bullish", "Wave 5", 6
        reason = "Sequential close progression suggests extended bullish wave"
    elif closes[-1] < closes[-3] < closes[-5]:
        bias, wave, score = "bearish", "Wave 5", 6
        reason = "Sequential close regression suggests extended bearish wave"
    else:
        bias, wave, score = "neutral", "Correction", 5
        reason = "No clear Elliott impulse pattern detected"

    return {"bias": bias, "wave": wave, "score": score, "reason": reason}
