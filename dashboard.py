"""Streamlit live dashboard for the Forex AI Signal Bot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forex_ai_bot import (
    add_features,
    analyze_symbol,
    fetch_yahoo_ohlc,
    get_trading_session,
    normalize_symbol,
    save_signals,
)

st.set_page_config(page_title="Forex AI Signal Dashboard", page_icon="📈", layout="wide")

CUSTOM_CSS = """
<style>
.big-title {font-size: 2.2rem; font-weight: 800; margin-bottom: 0.2rem;}
.subtle {color: #6b7280; font-size: 0.95rem;}
.card {padding: 1rem; border-radius: 16px; border: 1px solid #e5e7eb; background: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.04);}
.buy {color: #047857; font-weight: 800;}
.sell {color: #b91c1c; font-weight: 800;}
.wait {color: #6b7280; font-weight: 800;}
.warn {background: #fff7ed; padding: 0.75rem; border-radius: 12px; border: 1px solid #fed7aa;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown('<div class="big-title">📈 Forex AI Signal Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">Educational AI + technical-analysis scanner. Demo-test first. No profit guarantee.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Settings")
    default_symbols = os.getenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD")
    symbols_text = st.text_input("Pairs", value=default_symbols)
    timeframe = st.selectbox("Timeframe", ["15m", "30m", "1h", "4h", "1d"], index=2)
    period_default = "60d" if timeframe in {"15m", "30m"} else "180d"
    period = st.text_input("History period", value=period_default)
    min_strength = st.slider("Minimum signal strength", 0.55, 0.80, 0.62, 0.01)
    output_path = st.text_input("Save signals file", value=os.getenv("SIGNAL_OUTPUT", "latest_signals.csv"))
    auto_refresh = st.checkbox("Auto refresh page", value=False)
    refresh_seconds = st.slider("Refresh seconds", 30, 900, 300, 30)
    run_button = st.button("🔄 Refresh signals", type="primary")

if auto_refresh:
    st.markdown(f"<meta http-equiv='refresh' content='{refresh_seconds}'>", unsafe_allow_html=True)

session = get_trading_session()
col_s1, col_s2, col_s3, col_s4 = st.columns(4)
col_s1.metric("Active sessions", session["active_sessions"])
col_s2.metric("Session quality", session["session_quality"])
col_s3.metric("UTC time", session["utc_time"].replace(" UTC", ""))
col_s4.metric("FX market open", session["fx_market_open"])
st.info(session["session_advice"])

symbols = [normalize_symbol(x.strip()) for x in symbols_text.split(",") if x.strip()]
if not symbols:
    st.warning("Please enter at least one pair, for example EURUSD.")
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def cached_analyze(symbol: str, period: str, timeframe: str, min_strength: float):
    return analyze_symbol(symbol, period=period, timeframe=timeframe, min_strength=min_strength)

signals = []
placeholder = st.empty()

if run_button or True:
    with st.spinner("Scanning pairs and training quick AI models..."):
        for symbol in symbols:
            try:
                signals.append(cached_analyze(symbol, period, timeframe, min_strength))
            except Exception as exc:
                signals.append(
                    {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "symbol": symbol,
                        "action": "ERROR",
                        "signal_strength_pct": 0,
                        "last_price": None,
                        "reason": str(exc),
                    }
                )
    save_signals(signals, output_path)

signals_df = pd.DataFrame(signals)

if signals_df.empty:
    st.warning("No signals yet. Press Refresh signals.")
    st.stop()

tradable = signals_df[signals_df["action"].isin(["BUY", "SELL"])].copy()
if not tradable.empty:
    best = tradable.sort_values("signal_strength_pct", ascending=False).iloc[0]
    klass = "buy" if best["action"] == "BUY" else "sell"
    st.markdown(
        f"""
        <div class="card">
        <h3>Best signal right now</h3>
        <p><span class="{klass}">{best['action']} {best['symbol']}</span> — strength {best['signal_strength_pct']}%</p>
        <p>Entry: {best.get('entry')} | Stop Loss: {best.get('stop_loss')} | Take Profit: {best.get('take_profit')} | R:R {best.get('risk_reward')}</p>
        <p>{best.get('reason')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="warn"><b>Best advice right now:</b> WAIT. No pair passed the strength filter. Beginners should avoid forcing trades.</div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Live signal table")
show_cols = [
    "symbol",
    "timeframe",
    "action",
    "signal_strength_pct",
    "hybrid_prob_up",
    "ai_prob_up",
    "technical_score",
    "last_price",
    "entry",
    "stop_loss",
    "take_profit",
    "risk_reward",
    "rsi",
    "model_accuracy",
    "baseline_accuracy",
    "active_sessions",
    "session_quality",
    "reason",
]
existing = [c for c in show_cols if c in signals_df.columns]
st.dataframe(signals_df[existing], use_container_width=True, hide_index=True)

with st.expander("🛡️ Live safety / execution journal", expanded=False):
    st.write("Broker execution is OFF unless you deliberately enable it with safety environment variables.")
    risk_state_file = Path(os.getenv("RISK_STATE_FILE", "risk_state.json"))
    journal_file = Path(os.getenv("TRADE_JOURNAL_FILE", "trade_journal.csv"))
    if risk_state_file.exists():
        try:
            st.json(json.loads(risk_state_file.read_text(encoding="utf-8")))
        except Exception as exc:
            st.warning(f"Could not read risk state: {exc}")
    else:
        st.info("No risk_state.json yet. It appears after an execution attempt with account checks.")

    if journal_file.exists():
        try:
            journal_df = pd.read_csv(journal_file).tail(20)
            st.dataframe(journal_df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.warning(f"Could not read trade journal: {exc}")
    else:
        st.info("No trade_journal.csv yet. It appears after execution attempts.")

st.subheader("Signal strength gauges")
gauge_cols = st.columns(min(3, len(signals_df)))
for idx, (_, row) in enumerate(signals_df.sort_values("signal_strength_pct", ascending=False).head(3).iterrows()):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(row.get("signal_strength_pct", 0)),
            title={"text": f"{row.get('symbol')} {row.get('action')}"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2563eb"},
                "steps": [
                    {"range": [0, 55], "color": "#f3f4f6"},
                    {"range": [55, 62], "color": "#fde68a"},
                    {"range": [62, 100], "color": "#bbf7d0"},
                ],
                "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": min_strength * 100},
            },
        )
    )
    fig.update_layout(height=260, margin=dict(l=15, r=15, t=50, b=15))
    gauge_cols[idx % len(gauge_cols)].plotly_chart(fig, use_container_width=True)

st.subheader("Price chart")
selected = st.selectbox("Choose pair for chart", symbols, index=0)
if selected:
    try:
        chart_df = add_features(fetch_yahoo_ohlc(selected, period=period, interval=timeframe)).tail(250)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=chart_df.index,
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="Price",
        ))
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["ema_fast"], name="EMA 12", line=dict(color="#2563eb")))
        fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["ema_slow"], name="EMA 26", line=dict(color="#f97316")))
        latest_signal = signals_df[signals_df["symbol"] == selected]
        if not latest_signal.empty:
            row = latest_signal.iloc[0]
            for level_name, color in [("entry", "#111827"), ("stop_loss", "#dc2626"), ("take_profit", "#16a34a")]:
                if pd.notna(row.get(level_name)):
                    fig.add_hline(y=float(row[level_name]), line_dash="dash", line_color=color, annotation_text=level_name)
        fig.update_layout(height=560, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=35, b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.error(f"Chart error: {exc}")

st.caption(
    "This dashboard uses free Yahoo/yfinance data for education. For real execution, confirm every signal with broker-grade prices and a demo account."
)
