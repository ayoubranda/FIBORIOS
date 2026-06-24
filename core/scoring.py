from typing import Any, Dict

WEIGHTS: Dict[str, float] = {
    "elliott": 0.25,
    "price_action": 0.25,
    "market_structure": 0.25,
    "liquidity": 0.25,
}


def determine_signal(confidence: float) -> str:
    """Map the confidence value to the institutional signal framework."""
    if confidence >= 8.0:
        return "STRONG BUY"
    if confidence >= 6.0:
        return "BUY"
    if confidence >= 4.0:
        return "NEUTRAL"
    if confidence >= 2.0:
        return "SELL"
    return "STRONG SELL"


def evaluate_confidence(
    elliott: Dict[str, Any],
    price_action: Dict[str, Any],
    market_structure: Dict[str, Any],
    liquidity: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate institutional confidence from each analysis module."""
    confidence = round(
        elliott["score"] * WEIGHTS["elliott"] +
        price_action["score"] * WEIGHTS["price_action"] +
        market_structure["score"] * WEIGHTS["market_structure"] +
        liquidity["score"] * WEIGHTS["liquidity"],
        2
    )

    return {
        "confidence": confidence,
        "signal": determine_signal(confidence),
    }

