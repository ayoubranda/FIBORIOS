"""
Fibrios Trading Intelligence System — Streamlit frontend.
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

# ── Page config (must be first) ──────────────────────────────────────────────
st.set_page_config(
    page_title="Fibrios Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Remove Streamlit chrome */
#MainMenu, .stDeployButton, footer, header { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* Global */
body, .stApp { background: #0d1117; }

/* Engine cards */
.eng-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 18px 20px;
    height: 100%;
}
.eng-title {
    color: #8b949e;
    font-size: .72em;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: 8px;
}
.eng-val {
    color: #e6edf3;
    font-size: 1.05em;
    font-weight: 700;
    margin-bottom: 4px;
}
.eng-score-bar {
    background: #21262d;
    border-radius: 4px;
    height: 4px;
    margin: 10px 0 6px;
}
.eng-reason {
    color: #6e7681;
    font-size: .73em;
    line-height: 1.5;
    margin-top: 6px;
}

/* Trade plan cards */
.tp-row {
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #21262d;
    font-size: .88em;
}
.tp-label { color: #8b949e; }
.tp-value { color: #e6edf3; font-weight: 600; font-family: monospace; }

/* Narrative */
.narr-block {
    background: #0d1117;
    border: 1px solid #21262d;
    border-left: 3px solid #388bfd;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-size: .88em;
    line-height: 1.7;
    color: #c9d1d9;
}
.narr-label {
    color: #388bfd;
    font-size: .7em;
    text-transform: uppercase;
    letter-spacing: .1em;
    font-weight: 700;
    margin-bottom: 6px;
}

/* Divider */
.sec-title {
    color: #8b949e;
    font-size: .8em;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 600;
    margin: 20px 0 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────────────────────
SYMBOLS    = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "NAS100", "SPX500"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"]

_TV_SYMBOL = {
    "XAUUSD": "OANDA:XAUUSD",
    "XAGUSD": "OANDA:XAGUSD",
    "EURUSD": "FX:EURUSD",
    "GBPUSD": "FX:GBPUSD",
    "USDJPY": "FX:USDJPY",
    "NAS100": "NASDAQ:NDX",
    "SPX500": "SP:SPX",
}
_TV_INTERVAL = {
    "1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1D": "D",
}

# ── TradingView chart ────────────────────────────────────────────────────────
def _tv_widget(symbol: str, tf: str) -> str:
    tv_sym  = _TV_SYMBOL.get(symbol, f"OANDA:{symbol}")
    interval = _TV_INTERVAL.get(tf, "15")
    return f"""
    <div style="height:500px;border-radius:12px;overflow:hidden;">
      <div id="tv_c" style="height:100%;width:100%;"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
        new TradingView.widget({{
          autosize: true,
          symbol: "{tv_sym}",
          interval: "{interval}",
          timezone: "Etc/UTC",
          theme: "dark",
          style: "1",
          locale: "en",
          toolbar_bg: "#161b22",
          enable_publishing: false,
          hide_side_toolbar: false,
          allow_symbol_change: false,
          withdateranges: true,
          studies: ["RSI@tv-basicstudies"],
          container_id: "tv_c"
        }});
      </script>
    </div>"""

# ── Data helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _get_candles(symbol: str, tf: str) -> Optional[List[Dict]]:
    try:
        from backend.services.data_service import get_provider
        return get_provider().get_latest_candles(symbol, tf, 100)
    except Exception:
        return None

@st.cache_data(ttl=60, show_spinner=False)
def _get_price(symbol: str) -> Optional[float]:
    try:
        from backend.services.data_service import get_provider
        return get_provider().get_price(symbol)["price"]
    except Exception:
        return None

# ── Claude helper ─────────────────────────────────────────────────────────────
def _get_narrative(ctx: Dict, api_key: str) -> Optional[Dict]:
    try:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        from core.claude_engine import ClaudeAnalyzer
        return ClaudeAnalyzer().analyze(ctx)
    except Exception as e:
        return {"market_summary": f"Error: {e}", "trade_reasoning": "", "risks": "", "institutional_narrative": ""}

# ── Engine card renderer ──────────────────────────────────────────────────────
def _engine_card(col, title: str, main_val: str, bias: str, reason: str, score: int) -> None:
    b = bias.lower()
    if "bull" in b:
        bias_color, arrow = "#3fb950", "▲"
    elif "bear" in b:
        bias_color, arrow = "#f85149", "▼"
    else:
        bias_color, arrow = "#d29922", "◆"
    bar_color = "#3fb950" if score >= 7 else "#d29922" if score >= 5 else "#f85149"

    with col:
        st.markdown(f"""
        <div class="eng-card">
          <div class="eng-title">{title}</div>
          <div class="eng-val">{main_val}</div>
          <div style="color:{bias_color};font-size:.82em;font-weight:600">
            {arrow} {bias.upper()}
          </div>
          <div class="eng-score-bar">
            <div style="width:{score*10}%;background:{bar_color};height:100%;border-radius:4px;"></div>
          </div>
          <div style="color:#6e7681;font-size:.7em">Score {score}/10</div>
          <div class="eng-reason">{reason}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:1.4em;font-weight:800;color:#e6edf3'>📈 FIBRIOS</div>"
        "<div style='color:#6e7681;font-size:.8em;margin-bottom:16px'>Institutional Trading Intelligence</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    symbol    = st.selectbox("Asset", SYMBOLS)
    timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=2)

    st.divider()
    st.markdown(
        "<div style='color:#e6edf3;font-size:.85em;font-weight:600;margin-bottom:4px'>"
        "🔑 Claude API Key</div>"
        "<div style='color:#6e7681;font-size:.75em;margin-bottom:8px'>"
        "For AI narrative after engine analysis</div>",
        unsafe_allow_html=True,
    )
    api_key = st.text_input(
        label="api_key",
        type="password",
        placeholder="sk-ant-api03-...",
        label_visibility="collapsed",
    )
    if api_key:
        st.success("Claude narrative enabled ✓", icon="🤖")
    else:
        st.caption("Engines run fully without a key.")

    st.divider()
    run = st.button("▶  Run Analysis", use_container_width=True, type="primary")
    st.divider()

    st.markdown(
        "<div style='color:#484f58;font-size:.72em;line-height:1.8'>"
        "Charts · TradingView<br>"
        "Data · Yahoo Finance<br>"
        "Engines · Fibrios<br>"
        "AI · Claude Haiku</div>",
        unsafe_allow_html=True,
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='font-size:1.1em;font-weight:700;color:#e6edf3;margin-bottom:4px'>"
    f"{symbol} &nbsp;·&nbsp; {timeframe}</div>",
    unsafe_allow_html=True,
)

# ── TradingView chart ─────────────────────────────────────────────────────────
components.html(_tv_widget(symbol, timeframe), height=510, scrolling=False)

if not run:
    st.markdown(
        "<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;"
        "padding:20px 24px;color:#8b949e;text-align:center;margin-top:12px'>"
        "Select an asset and timeframe in the sidebar, then click <b style='color:#e6edf3'>▶ Run Analysis</b>."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Run engines ───────────────────────────────────────────────────────────────
with st.spinner("Running Fibrios engines…"):
    candles = _get_candles(symbol, timeframe)
    price   = _get_price(symbol)

    e_res = analyze_elliott(candles)
    p_res = analyze_price_action(candles)
    m_res = analyze_market_structure(candles)
    l_res = analyze_liquidity(candles)
    final = evaluate_confidence(
        elliott=e_res, price_action=p_res,
        market_structure=m_res, liquidity=l_res,
    )
    plan = generate_trade_plan(
        signal=final["signal"],
        confidence=final["confidence"],
        price=price,
    )

signal     = final["signal"]
confidence = final["confidence"]

# ── Signal banner ─────────────────────────────────────────────────────────────
if "BUY" in signal:
    bg, border, icon = "#0d2818", "#3fb950", "🟢"
elif "SELL" in signal:
    bg, border, icon = "#2d0f0f", "#f85149", "🔴"
else:
    bg, border, icon = "#1c1a0a", "#d29922", "🟡"

st.markdown(f"""
<div style="background:{bg};border-left:4px solid {border};border-radius:10px;
padding:16px 24px;margin:14px 0;display:flex;align-items:center;justify-content:space-between;">
  <div>
    <div style="color:#8b949e;font-size:.7em;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">
      Fibrios Signal
    </div>
    <div style="color:{border};font-size:1.7em;font-weight:800;letter-spacing:.04em">
      {icon} {signal}
    </div>
  </div>
  <div style="text-align:right">
    <div style="color:#8b949e;font-size:.7em;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">
      Confidence
    </div>
    <div style="color:#e6edf3;font-size:1.7em;font-weight:800">
      {confidence}<span style="font-size:.55em;color:#8b949e"> / 10</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Price row
if price:
    price_fmt = f"{price:,.5g}"
    st.markdown(
        f"<span style='background:#161b22;border:1px solid #30363d;border-radius:20px;"
        f"padding:4px 14px;font-family:monospace;font-size:.9em;color:#e6edf3'>"
        f"💰 {symbol} &nbsp;{price_fmt}</span>"
        f"<span style='color:#484f58;font-size:.72em;margin-left:10px'>"
        f"Yahoo Finance · may differ slightly from TradingView spot</span>",
        unsafe_allow_html=True,
    )

# ── Engine cards ──────────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>Engine Analysis</div>", unsafe_allow_html=True)
r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

_engine_card(r1c1, "Elliott Wave",     e_res.get("wave","—"),      e_res.get("bias","—"), e_res.get("reason",""), e_res.get("score",5))
_engine_card(r1c2, "Market Structure", m_res.get("structure","—"), m_res.get("trend","—"), m_res.get("reason",""), m_res.get("score",5))
_engine_card(r2c1, "Price Action",     p_res.get("pattern","—"),   p_res.get("bias","—"), p_res.get("reason",""), p_res.get("score",5))
_engine_card(r2c2, "Liquidity",        l_res.get("sweep","—"),     l_res.get("bias","—"), l_res.get("reason",""), l_res.get("score",5))

# ── Trade plan ────────────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>Trade Plan</div>", unsafe_allow_html=True)
tp1, tp2 = st.columns(2)

with tp1:
    st.markdown(f"""
    <div class="eng-card">
      <div class="eng-title">Entry &amp; Stop</div>
      <div class="tp-row">
        <span class="tp-label">Aggressive entry</span>
        <span class="tp-value">{plan['entry_aggressive']}</span>
      </div>
      <div class="tp-row">
        <span class="tp-label">Balanced entry</span>
        <span style="color:#388bfd;font-weight:700;font-family:monospace">{plan['entry_balanced']}</span>
      </div>
      <div class="tp-row">
        <span class="tp-label">Conservative entry</span>
        <span class="tp-value">{plan['entry_conservative']}</span>
      </div>
      <div class="tp-row" style="border:none">
        <span class="tp-label">Stop Loss</span>
        <span style="color:#f85149;font-weight:700;font-family:monospace">{plan['stop_loss']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

with tp2:
    st.markdown(f"""
    <div class="eng-card">
      <div class="eng-title">Targets</div>
      <div class="tp-row">
        <span class="tp-label">TP1</span>
        <span style="color:#3fb950;font-weight:700;font-family:monospace">{plan['tp1']}</span>
      </div>
      <div class="tp-row">
        <span class="tp-label">TP2</span>
        <span style="color:#3fb950;font-weight:700;font-family:monospace">{plan['tp2']}</span>
      </div>
      <div class="tp-row">
        <span class="tp-label">TP3</span>
        <span style="color:#3fb950;font-weight:700;font-family:monospace">{plan['tp3']}</span>
      </div>
      <div class="tp-row" style="border:none">
        <span class="tp-label">Risk / Reward</span>
        <span style="color:#d29922;font-weight:700;font-family:monospace">{plan['risk_reward']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Claude narrative ──────────────────────────────────────────────────────────
st.markdown("<div class='sec-title'>Claude Narrative</div>", unsafe_allow_html=True)

if not api_key:
    st.markdown("""
    <div style="background:#161b22;border:1px dashed #30363d;border-radius:10px;
    padding:28px;text-align:center;color:#6e7681;">
      <div style="font-size:1.5em;margin-bottom:8px">🔑</div>
      Enter your <b style="color:#e6edf3">Claude API Key</b> in the sidebar to unlock AI narrative.<br>
      <span style="font-size:.82em">Fibrios engines are running fully without it.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    ctx = {
        "symbol": symbol, "timeframe": timeframe,
        "signal": signal, "confidence": confidence,
        "elliott_bias": e_res["bias"],
        "market_structure": m_res["structure"],
        "liquidity": l_res["sweep"],
        "price_action": p_res["pattern"],
    }
    with st.spinner("Generating Claude narrative…"):
        narrative = _get_narrative(ctx, api_key)

    if narrative:
        for label, key in [
            ("Market Summary",        "market_summary"),
            ("Trade Reasoning",       "trade_reasoning"),
            ("Risks",                 "risks"),
            ("Institutional Narrative","institutional_narrative"),
        ]:
            text = narrative.get(key, "")
            if text:
                st.markdown(f"""
                <div class="narr-block">
                  <div class="narr-label">{label}</div>
                  {text}
                </div>
                """, unsafe_allow_html=True)
