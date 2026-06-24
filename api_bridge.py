"""
FastAPI bridge for MetaTrader Expert Advisors.

Run locally:
    uvicorn api_bridge:app --host 0.0.0.0 --port 8000

Endpoints:
    /latest.txt?symbol=EURUSD   -> EURUSD|BUY|0.70|1.08000|1.07500|1.09000|timestamp
    /latest.json?symbol=EURUSD  -> JSON signal
    /scan?secret=...            -> refreshes signals using env settings
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from forex_ai_bot import bridge_line, normalize_symbol, scan_symbols, signals_from_env

app = FastAPI(title="Forex AI Bot Bridge", version="0.1.0")


def _check_secret(secret: Optional[str]) -> None:
    expected = os.getenv("API_SHARED_SECRET", "").strip()
    if expected and expected != "change_me_optional" and secret != expected:
        raise HTTPException(status_code=401, detail="Invalid secret")


def _load_signal(symbol: str):
    output_path = os.getenv("SIGNAL_OUTPUT", "latest_signals.csv")
    clean = normalize_symbol(symbol)
    if not Path(output_path).exists():
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": clean,
            "action": "WAIT",
            "signal_strength": 0,
            "entry": "",
            "stop_loss": "",
            "take_profit": "",
            "reason": "No latest_signals.csv yet. Run /scan first.",
        }
    df = pd.read_csv(output_path)
    if df.empty:
        raise HTTPException(status_code=404, detail="Signal file is empty")
    df["symbol_clean"] = df["symbol"].astype(str).map(normalize_symbol)
    match = df[df["symbol_clean"] == clean]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"No signal for {clean}")
    row = match.iloc[0].drop(labels=["symbol_clean"], errors="ignore")
    # Convert NaN to None/empty strings.
    data = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
    return data


@app.get("/")
def home():
    return {
        "name": "Forex AI Bot Bridge",
        "message": "Use /latest.txt?symbol=EURUSD or /latest.json?symbol=EURUSD",
        "warning": "Educational/demo bridge. Protect it with API_SHARED_SECRET before connecting trading platforms.",
    }


@app.get("/latest.txt", response_class=PlainTextResponse)
def latest_txt(symbol: str = "EURUSD", secret: Optional[str] = Query(default=None)):
    _check_secret(secret)
    return bridge_line(_load_signal(symbol))


@app.get("/latest.json")
def latest_json(symbol: str = "EURUSD", secret: Optional[str] = Query(default=None)):
    _check_secret(secret)
    return _load_signal(symbol)


@app.get("/scan")
def scan(secret: Optional[str] = Query(default=None)):
    _check_secret(secret)
    signals = scan_symbols(
        symbols=signals_from_env(),
        period=os.getenv("PERIOD", "180d"),
        timeframe=os.getenv("TIMEFRAME", "1h"),
        min_strength=float(os.getenv("MIN_SIGNAL_STRENGTH", "0.62")),
        output_path=os.getenv("SIGNAL_OUTPUT", "latest_signals.csv"),
        email=False,
        execute=False,
    )
    return {"count": len(signals), "signals": signals}
