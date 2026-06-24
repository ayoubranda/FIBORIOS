from typing import Any, Dict, Optional


def generate_trade_plan(
    signal: str,
    confidence: float,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate an institutional trade plan from the Fibrios signal and confidence score.

    price: current market price from the data layer (falls back to placeholder if None).
    """
    base = price if price is not None else 100.0
    is_buy = "BUY" in signal.upper()

    # Risk offset scales with confidence (higher confidence → tighter stops)
    risk_pct = max(0.005, 0.02 - (confidence / 10) * 0.01)
    risk_abs = base * risk_pct
    rr_tp1, rr_tp2, rr_tp3 = 1.5, 3.0, 5.0

    if is_buy:
        stop_loss = base - risk_abs
        tp1 = base + risk_abs * rr_tp1
        tp2 = base + risk_abs * rr_tp2
        tp3 = base + risk_abs * rr_tp3
        entry_agg = base - risk_abs * 0.25
        entry_con = base + risk_abs * 0.25
    else:
        stop_loss = base + risk_abs
        tp1 = base - risk_abs * rr_tp1
        tp2 = base - risk_abs * rr_tp2
        tp3 = base - risk_abs * rr_tp3
        entry_agg = base + risk_abs * 0.25
        entry_con = base - risk_abs * 0.25

    rr = round(abs(tp1 - base) / abs(base - stop_loss), 2)

    def fmt(v: float) -> str:
        return f"{v:.5g}"

    return {
        "entry_aggressive": fmt(entry_agg),
        "entry_balanced": fmt(base),
        "entry_conservative": fmt(entry_con),
        "stop_loss": fmt(stop_loss),
        "tp1": fmt(tp1),
        "tp2": fmt(tp2),
        "tp3": fmt(tp3),
        "risk_reward": f"{rr}:1",
    }
