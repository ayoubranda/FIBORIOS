"""
Fibrios CLI entry point.

Fetches live data from TradingView (when available) and runs all engines.
Usage: python main.py [SYMBOL] [TIMEFRAME]
"""
import sys
from typing import Any, Dict, Optional, List

from core.elliott_engine import analyze as analyze_elliott
from core.liquidity import analyze as analyze_liquidity
from core.market_structure import analyze as analyze_market_structure
from core.price_action import analyze as analyze_price_action
from core.scoring import evaluate_confidence
from core.trade_generator import generate_trade_plan


def _fetch(symbol: str, timeframe: str) -> tuple:
    """Return (candles, price) from TradingView; falls back to (None, None)."""
    try:
        from backend.services.data_service import get_provider
        provider = get_provider()
        candles = provider.get_latest_candles(symbol, timeframe, count=100)
        price = provider.get_price(symbol)["price"]
        return candles, price
    except Exception as exc:
        print(f"[data] Live data unavailable ({exc}). Running in demo mode.\n")
        return None, None


def render_section(title: str, data: Dict[str, Any]) -> None:
    print(title)
    for label, value in data.items():
        print(f"  {label}: {value}")
    print()


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "15m"

    print("# " + "=" * 39)
    print("FIBRIOS Trading Intelligence System")
    print(f"  Symbol: {symbol}  |  Timeframe: {timeframe}")
    print("# " + "=" * 39 + "\n")

    candles, price = _fetch(symbol, timeframe)

    elliott_result = analyze_elliott(candles)
    price_action_result = analyze_price_action(candles)
    market_result = analyze_market_structure(candles)
    liquidity_result = analyze_liquidity(candles)

    final_report = evaluate_confidence(
        elliott=elliott_result,
        price_action=price_action_result,
        market_structure=market_result,
        liquidity=liquidity_result,
    )

    render_section("ELLIOTT WAVE", {
        "Wave": elliott_result["wave"],
        "Bias": elliott_result["bias"],
        "Reason": elliott_result["reason"],
    })
    render_section("PRICE ACTION", {
        "Pattern": price_action_result["pattern"],
        "Bias": price_action_result["bias"],
        "Reason": price_action_result["reason"],
    })
    render_section("MARKET STRUCTURE", {
        "Structure": market_result["structure"],
        "Trend": market_result["trend"],
        "Reason": market_result["reason"],
    })
    render_section("LIQUIDITY", {
        "Sweep": liquidity_result["sweep"],
        "Bias": liquidity_result["bias"],
        "Reason": liquidity_result["reason"],
    })

    trade_plan = generate_trade_plan(
        signal=final_report["signal"],
        confidence=final_report["confidence"],
        price=price,
    )

    print("# " + "=" * 39)
    print("FINAL DECISION")
    print(f"  Confidence: {final_report['confidence']}/10")
    print(f"  Signal:     {final_report['signal']}")
    print("# " + "=" * 39 + "\n")

    print("TRADE PLAN")
    print(f"  Entry Aggressive:   {trade_plan['entry_aggressive']}")
    print(f"  Entry Balanced:     {trade_plan['entry_balanced']}")
    print(f"  Entry Conservative: {trade_plan['entry_conservative']}")
    print(f"  Stop Loss:          {trade_plan['stop_loss']}")
    print(f"  TP1: {trade_plan['tp1']}  TP2: {trade_plan['tp2']}  TP3: {trade_plan['tp3']}")
    print(f"  Risk/Reward:        {trade_plan['risk_reward']}")

    # Claude narrative (optional)
    import os
    if os.getenv("ANTHROPIC_API_KEY"):
        signal_context = {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": final_report["signal"],
            "confidence": final_report["confidence"],
            "elliott_bias": elliott_result["bias"],
            "market_structure": market_result["structure"],
            "liquidity": liquidity_result["sweep"],
            "price_action": price_action_result["pattern"],
        }
        try:
            from core.claude_engine import ClaudeAnalyzer
            narrative = ClaudeAnalyzer().analyze(signal_context)
            print("\nCLAUDE NARRATIVE")
            for key, val in narrative.items():
                print(f"  {key.replace('_', ' ').title()}: {val}")
        except Exception as exc:
            print(f"\n[claude] Narrative unavailable: {exc}")


if __name__ == "__main__":
    main()
