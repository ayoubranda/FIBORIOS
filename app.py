"""
Fibrios Trading Intelligence System — Streamlit frontend.

Layout:
  Left  (65 %): TradingView Advanced Chart
  Right (35 %): Asset selector + Engine results + Claude narrative
"""
import os
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

from core.elliott_engine import analyze as analyze_elliott
from core.liquidity import analyze as analyze_liquidity
from core.market_structure import analyze as analyze_market_structure
from core.price_action import analyze as analyze_price_action
from core.scoring import evaluate_confidence
from core.trade_generator import generate_trade_plan

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SYMBOLS = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "NAS100", "SPX500"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"]

# TradingView symbol format used by the widget
_TV_WIDGET_SYMBOL: Dict[str, str] = {
    "XAUUSD": "OANDA:XAUUSD",
    "XAGUSD": "OANDA:XAGUSD",
    "EURUSD": "FX:EURUSD",
    "GBPUSD": "FX:GBPUSD",
    "USDJPY": "FX:USDJPY",
    "NAS100": "OANDA:NAS100",
    "SPX500": "OANDA:SPX500",
}

_TV_INTERVAL: Dict[str, str] = {
    "1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1D": "D",
}

# ---------------------------------------------------------------------------
# TradingView chart widget
# ---------------------------------------------------------------------------

def _tradingview_widget(symbol: str, timeframe: str, theme: str = "dark") -> str:
    tv_symbol = _TV_WIDGET_SYMBOL.get(symbol, f"OANDA:{symbol}")
    interval = _TV_INTERVAL.get(timeframe, "15")
    return f"""
    <div class="tradingview-widget-container" style="height:520px;width:100%;">
      <div id="tv_chart" style="height:100%;width:100%;"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
        new TradingView.widget({{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "{interval}",
          "timezone": "Etc/UTC",
          "theme": "{theme}",
          "style": "1",
          "locale": "en",
          "toolbar_bg": "#1e222d",
          "enable_publishing": false,
          "hide_side_toolbar": false,
          "allow_symbol_change": false,
          "withdateranges": true,
          "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies"],
          "container_id": "tv_chart"
        }});
      </script>
    </div>
    """


# ---------------------------------------------------------------------------
# Data fetching (TradingView via data_service)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_candles(symbol: str, timeframe: str, count: int = 100) -> Optional[List[Dict[str, Any]]]:
    try:
        from backend.services.data_service import get_provider
        provider = get_provider()
        return provider.get_latest_candles(symbol, timeframe, count)
    except Exception as exc:
        st.warning(f"Live data unavailable ({exc}). Running engines in demo mode.")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_price(symbol: str) -> Optional[float]:
    try:
        from backend.services.data_service import get_provider
        provider = get_provider()
        return provider.get_price(symbol)["price"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Claude narrative (optional — requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------

def _claude_narrative(signal_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from core.claude_engine import ClaudeAnalyzer
        return ClaudeAnalyzer().analyze(signal_context)
    except Exception as exc:
        st.warning(f"Claude narrative unavailable: {exc}")
        return None


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _metric_row(label: str, value: str, delta: Optional[str] = None) -> None:
    st.metric(label=label, value=value, delta=delta)


def _section(title: str, data: Dict[str, Any], keys: List[str]) -> None:
    with st.expander(title, expanded=True):
        cols = st.columns(len(keys))
        for col, key in zip(cols, keys):
            col.metric(key.replace("_", " ").title(), data.get(key, "—"))
        st.caption(data.get("reason", ""))


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Fibrios Intelligence",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        "<h2 style='margin-bottom:0'>📈 Fibrios Trading Intelligence</h2>"
        "<p style='color:#888;margin-top:0'>Powered by TradingView · Fibrios Engines · Claude AI</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ----- Controls row -----
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
    with ctrl1:
        symbol = st.selectbox("Asset", SYMBOLS, index=0)
    with ctrl2:
        timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=2)  # default 15m
    with ctrl3:
        st.write("")
        st.write("")
        run = st.button("▶ Run Analysis", use_container_width=True, type="primary")

    # ----- Main layout: chart + panel -----
    chart_col, panel_col = st.columns([65, 35])

    with chart_col:
        components.html(
            _tradingview_widget(symbol, timeframe),
            height=530,
            scrolling=False,
        )

    with panel_col:
        if not run:
            st.info("Select an asset and timeframe, then click **▶ Run Analysis**.")
            return

        with st.spinner(f"Running Fibrios engines on {symbol}/{timeframe}…"):
            candles = _fetch_candles(symbol, timeframe)
            price = _fetch_price(symbol)

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

            trade_plan = generate_trade_plan(
                signal=final_report["signal"],
                confidence=final_report["confidence"],
                price=price,
            )

        # ---- Signal header ----
        signal = final_report["signal"]
        confidence = final_report["confidence"]
        color = "#00c853" if "BUY" in signal else ("#e53935" if "SELL" in signal else "#ffa726")
        st.markdown(
            f"<div style='background:{color}22;border-left:4px solid {color};"
            f"padding:12px 16px;border-radius:6px;margin-bottom:12px'>"
            f"<b style='font-size:1.3em;color:{color}'>{signal}</b> &nbsp;"
            f"<span style='color:#ccc'>Confidence {confidence}/10</span></div>",
            unsafe_allow_html=True,
        )

        if price:
            st.metric("Current Price", f"{price:,.5g}")

        # ---- Engine results ----
        st.subheader("Engine Analysis")
        _section(
            "Elliott Wave",
            elliott_result,
            ["wave", "bias"],
        )
        _section(
            "Price Action",
            price_action_result,
            ["pattern", "bias"],
        )
        _section(
            "Market Structure",
            market_result,
            ["structure", "trend"],
        )
        _section(
            "Liquidity",
            liquidity_result,
            ["sweep", "bias"],
        )

        # ---- Trade Plan ----
        st.subheader("Trade Plan")
        t1, t2 = st.columns(2)
        t1.metric("Entry (Balanced)", trade_plan["entry_balanced"])
        t2.metric("Stop Loss", trade_plan["stop_loss"])
        tp1_col, tp2_col, tp3_col = st.columns(3)
        tp1_col.metric("TP1", trade_plan["tp1"])
        tp2_col.metric("TP2", trade_plan["tp2"])
        tp3_col.metric("TP3", trade_plan["tp3"])
        st.caption(f"Risk/Reward: **{trade_plan['risk_reward']}** · "
                   f"Aggressive entry: {trade_plan['entry_aggressive']} · "
                   f"Conservative entry: {trade_plan['entry_conservative']}")

        # ---- Claude Narrative (if API key present) ----
        signal_context = {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal,
            "confidence": confidence,
            "elliott_bias": elliott_result["bias"],
            "market_structure": market_result["structure"],
            "liquidity": liquidity_result["sweep"],
            "price_action": price_action_result["pattern"],
        }

        with st.spinner("Generating Claude narrative…"):
            narrative = _claude_narrative(signal_context)

        if narrative:
            st.subheader("Claude Narrative")
            st.markdown(f"> {narrative.get('market_summary', '')}")
            with st.expander("Full narrative"):
                if narrative.get("trade_reasoning"):
                    st.markdown(f"**Reasoning:** {narrative['trade_reasoning']}")
                if narrative.get("risks"):
                    st.markdown(f"**Risks:** {narrative['risks']}")
                if narrative.get("institutional_narrative"):
                    st.markdown(f"**Institutional:** {narrative['institutional_narrative']}")
        else:
            st.caption("Set `ANTHROPIC_API_KEY` to enable Claude narrative.")


if __name__ == "__main__":
    main()
