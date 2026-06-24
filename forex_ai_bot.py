"""
Forex AI Signal Bot - educational starter kit.

IMPORTANT:
- This is not financial advice.
- The model is a learning/demo template, not a profit guarantee.
- Broker execution is OFF by default. Use demo/paper accounts first.
"""

from __future__ import annotations

import json
import math
import os
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

load_dotenv()

FX_YAHOO_SYMBOLS: Dict[str, str] = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",      # Yahoo uses JPY=X for USD/JPY
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",      # Yahoo uses CAD=X for USD/CAD
    "USDCHF": "CHF=X",      # Yahoo uses CHF=X for USD/CHF
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "XAUUSD": "GC=F",       # Gold futures proxy, not spot XAUUSD
}

FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_6",
    "ema_fast_gap",
    "ema_slow_gap",
    "ema_trend",
    "macd_gap",
    "rsi",
    "atr_pct",
    "volatility_12",
    "volatility_24",
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_symbol(symbol: str) -> str:
    """Turn EUR/USD, EUR_USD, eurusd into EURUSD."""
    return "".join(ch for ch in str(symbol).upper() if ch.isalnum())


def symbol_for_yahoo(symbol: str) -> str:
    clean = normalize_symbol(symbol)
    return FX_YAHOO_SYMBOLS.get(clean, f"{clean}=X")


def symbol_for_oanda(symbol: str) -> str:
    clean = normalize_symbol(symbol)
    if len(clean) == 6:
        return clean[:3] + "_" + clean[3:]
    if clean == "XAUUSD":
        return "XAU_USD"
    return clean


def fetch_yahoo_ohlc(symbol: str, period: str = "180d", interval: str = "1h") -> pd.DataFrame:
    """
    Fetch OHLC data from Yahoo Finance via yfinance.

    Good for learning and dashboards. For broker-quality live execution, use your
    broker data feed because free feeds can be delayed or incomplete.
    """
    ticker = symbol_for_yahoo(symbol)
    raw = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )

    if raw is None or raw.empty:
        raise RuntimeError(f"No Yahoo Finance data returned for {symbol} ({ticker}).")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.rename(columns={c: c.lower().replace(" ", "_") for c in raw.columns})
    rename_map = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "adj_close": "adj_close",
        "volume": "volume",
    }
    df = df.rename(columns=rename_map)

    # Some FX data has volume missing or zero. We keep a volume column for compatibility.
    if "volume" not in df.columns:
        df["volume"] = 0

    needed = ["open", "high", "low", "close", "volume"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns for {symbol}: {missing}. Columns: {list(df.columns)}")

    df = df[needed].copy()
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    value = 100 - (100 / (1 + rs))
    return value.fillna(50)


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def add_features(df: pd.DataFrame, lookahead: int = 1) -> pd.DataFrame:
    """Create technical-analysis + time features and a next-candle target."""
    out = df.copy()
    close = out["close"]

    out["return_1"] = close.pct_change(1)
    out["return_3"] = close.pct_change(3)
    out["return_6"] = close.pct_change(6)

    out["ema_fast"] = close.ewm(span=12, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=26, adjust=False).mean()
    out["ema_fast_gap"] = (close - out["ema_fast"]) / close
    out["ema_slow_gap"] = (close - out["ema_slow"]) / close
    out["ema_trend"] = (out["ema_fast"] - out["ema_slow"]) / close

    out["macd"] = out["ema_fast"] - out["ema_slow"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_gap"] = (out["macd"] - out["macd_signal"]) / close

    out["rsi"] = rsi(close, 14)
    out["atr"] = atr(out, 14)
    out["atr_pct"] = out["atr"] / close
    out["volatility_12"] = out["return_1"].rolling(12).std()
    out["volatility_24"] = out["return_1"].rolling(24).std()

    idx = pd.to_datetime(out.index, utc=True)
    hours = idx.hour + idx.minute / 60.0
    days = idx.dayofweek
    out["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hours / 24)
    out["day_sin"] = np.sin(2 * np.pi * days / 7)
    out["day_cos"] = np.cos(2 * np.pi * days / 7)

    out["future_return"] = close.pct_change(lookahead).shift(-lookahead)
    out["target"] = np.nan
    out.loc[out["future_return"] > 0, "target"] = 1
    out.loc[out["future_return"] <= 0, "target"] = 0

    return out.replace([np.inf, -np.inf], np.nan)


def technical_score(row: pd.Series) -> float:
    """Simple rule-based score from -1.0 bearish to +1.0 bullish."""
    score = 0.0
    max_score = 5.0

    score += 1 if row["close"] > row["ema_slow"] else -1
    score += 1 if row["ema_fast"] > row["ema_slow"] else -1
    score += 1 if row["macd"] > row["macd_signal"] else -1

    if row["rsi"] >= 60:
        score += 1
    elif row["rsi"] <= 40:
        score -= 1

    # Avoid chasing very overbought/oversold areas too aggressively.
    if 45 <= row["rsi"] <= 70:
        score += 0.5
    elif 30 <= row["rsi"] <= 55:
        score -= 0.5

    return float(max(-1, min(1, score / max_score)))


def market_open_now(now_utc: Optional[datetime] = None) -> bool:
    """Approximate FX market hours: Sunday 22:00 UTC to Friday 22:00 UTC."""
    now = now_utc or datetime.now(timezone.utc)
    weekday = now.weekday()  # Mon=0 ... Sun=6
    hour = now.hour
    if weekday == 5:  # Saturday
        return False
    if weekday == 6 and hour < 22:
        return False
    if weekday == 4 and hour >= 22:
        return False
    return True


def get_trading_session(now_utc: Optional[datetime] = None) -> Dict[str, str]:
    """Return currently active major sessions using local exchange time zones."""
    now = now_utc or datetime.now(timezone.utc)

    sessions = []
    local_times = {}
    definitions = [
        ("Asia/Tokyo", "Tokyo", 9, 18),
        ("Europe/London", "London", 8, 17),
        ("America/New_York", "New York", 8, 17),
    ]

    for tz_name, label, start_hour, end_hour in definitions:
        local = now.astimezone(ZoneInfo(tz_name))
        local_times[label] = local.strftime("%H:%M")
        if start_hour <= local.hour < end_hour and local.weekday() < 5:
            sessions.append(label)

    active = ", ".join(sessions) if sessions else "Quiet/off-session"

    if "London" in sessions and "New York" in sessions:
        quality = "HIGH"
        advice = "Best liquidity: London + New York overlap. Spreads are usually tighter."
    elif "London" in sessions:
        quality = "GOOD"
        advice = "Good liquidity: London session is active."
    elif "New York" in sessions:
        quality = "GOOD"
        advice = "Good liquidity: New York session is active."
    elif "Tokyo" in sessions:
        quality = "MEDIUM"
        advice = "Asian session: often calmer unless trading JPY/AUD/NZD pairs."
    else:
        quality = "LOW"
        advice = "Quiet period: avoid weak signals and watch spreads."

    return {
        "active_sessions": active,
        "session_quality": quality,
        "session_advice": advice,
        "utc_time": now.strftime("%Y-%m-%d %H:%M UTC"),
        "tokyo_time": local_times.get("Tokyo", ""),
        "london_time": local_times.get("London", ""),
        "new_york_time": local_times.get("New York", ""),
        "fx_market_open": str(market_open_now(now)),
    }


def train_model_and_predict(featured: pd.DataFrame) -> Dict[str, float]:
    """Train a small random forest and predict probability of next candle going up."""
    data = featured.dropna(subset=FEATURE_COLUMNS).copy()
    train_data = data.dropna(subset=["target"]).copy()

    if len(train_data) < 120 or train_data["target"].nunique() < 2:
        # Fallback: no enough data. Use neutral ML probability.
        return {
            "prob_up": 0.50,
            "accuracy": np.nan,
            "baseline_accuracy": np.nan,
            "train_rows": float(len(train_data)),
        }

    train_data["target"] = train_data["target"].astype(int)
    split = int(len(train_data) * 0.8)
    split = max(80, min(split, len(train_data) - 20))

    train = train_data.iloc[:split]
    test = train_data.iloc[split:]

    X_train = train[FEATURE_COLUMNS]
    y_train = train["target"]
    X_test = test[FEATURE_COLUMNS]
    y_test = test["target"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    if len(test) > 0 and y_test.nunique() >= 1:
        preds = model.predict(X_test)
        acc = float(accuracy_score(y_test, preds))
        baseline = float(max(y_test.mean(), 1 - y_test.mean()))
    else:
        acc = np.nan
        baseline = np.nan

    latest = data.iloc[[-1]][FEATURE_COLUMNS]
    classes = list(model.classes_)
    probs = model.predict_proba(latest)[0]
    prob_up = float(probs[classes.index(1)] if 1 in classes else 0.5)

    return {
        "prob_up": prob_up,
        "accuracy": acc,
        "baseline_accuracy": baseline,
        "train_rows": float(len(train_data)),
    }


def price_decimals(symbol: str) -> int:
    clean = normalize_symbol(symbol)
    if "JPY" in clean:
        return 3
    if clean == "XAUUSD":
        return 2
    return 5


def build_levels(symbol: str, action: str, entry: float, atr_value: float) -> Dict[str, Optional[float]]:
    """Create ATR-based stop-loss/take-profit levels."""
    decimals = price_decimals(symbol)
    rounded_entry = round(float(entry), decimals)
    if action not in {"BUY", "SELL"} or not np.isfinite(atr_value) or atr_value <= 0:
        return {"entry": rounded_entry, "stop_loss": None, "take_profit": None, "risk_reward": None}

    sl_distance = 1.5 * atr_value
    tp_distance = 2.25 * atr_value

    if action == "BUY":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:
        sl = entry + sl_distance
        tp = entry - tp_distance

    return {
        "entry": round(float(entry), decimals),
        "stop_loss": round(float(sl), decimals),
        "take_profit": round(float(tp), decimals),
        "risk_reward": round(float(tp_distance / sl_distance), 2),
    }


def analyze_symbol(
    symbol: str,
    period: str = "180d",
    timeframe: str = "1h",
    min_strength: float = 0.62,
) -> Dict[str, object]:
    """Fetch data, train the model, and create a single signal dictionary."""
    clean_symbol = normalize_symbol(symbol)
    df = fetch_yahoo_ohlc(clean_symbol, period=period, interval=timeframe)
    featured = add_features(df)
    model_info = train_model_and_predict(featured)
    latest = featured.dropna(subset=FEATURE_COLUMNS).iloc[-1]

    tech = technical_score(latest)
    ml_prob_up = model_info["prob_up"]
    technical_prob_up = (tech + 1) / 2
    hybrid_prob_up = 0.65 * ml_prob_up + 0.35 * technical_prob_up

    strength = max(hybrid_prob_up, 1 - hybrid_prob_up)
    action = "WAIT"
    if hybrid_prob_up >= min_strength:
        action = "BUY"
    elif hybrid_prob_up <= (1 - min_strength):
        action = "SELL"

    now = datetime.now(timezone.utc)
    session = get_trading_session(now)
    if not market_open_now(now):
        action = "WAIT"
        session["session_advice"] = "FX market is closed. Do not place new market trades."

    levels = build_levels(clean_symbol, action, float(latest["close"]), float(latest["atr"]))

    reasons = []
    reasons.append(f"AI up-prob={ml_prob_up:.2f}")
    reasons.append(f"technical score={tech:+.2f}")
    if latest["ema_fast"] > latest["ema_slow"]:
        reasons.append("EMA trend bullish")
    else:
        reasons.append("EMA trend bearish")
    if latest["macd"] > latest["macd_signal"]:
        reasons.append("MACD bullish")
    else:
        reasons.append("MACD bearish")
    reasons.append(f"RSI={latest['rsi']:.1f}")
    reasons.append(session["session_quality"] + " session")

    result = {
        "timestamp_utc": now.isoformat(timespec="seconds"),
        "symbol": clean_symbol,
        "timeframe": timeframe,
        "action": action,
        "signal_strength": round(float(strength), 4),
        "signal_strength_pct": round(float(strength * 100), 1),
        "hybrid_prob_up": round(float(hybrid_prob_up), 4),
        "ai_prob_up": round(float(ml_prob_up), 4),
        "technical_score": round(float(tech), 4),
        "last_price": round(float(latest["close"]), price_decimals(clean_symbol)),
        "entry": levels["entry"],
        "stop_loss": levels["stop_loss"],
        "take_profit": levels["take_profit"],
        "risk_reward": levels["risk_reward"],
        "rsi": round(float(latest["rsi"]), 2),
        "atr": round(float(latest["atr"]), price_decimals(clean_symbol)),
        "model_accuracy": None if np.isnan(model_info["accuracy"]) else round(float(model_info["accuracy"]), 4),
        "baseline_accuracy": None if np.isnan(model_info["baseline_accuracy"]) else round(float(model_info["baseline_accuracy"]), 4),
        "train_rows": int(model_info["train_rows"]),
        "active_sessions": session["active_sessions"],
        "session_quality": session["session_quality"],
        "session_advice": session["session_advice"],
        "fx_market_open": session["fx_market_open"],
        "reason": "; ".join(reasons),
        "data_provider": "Yahoo Finance/yfinance",
        "warning": "Educational signal only. Demo-test before any real-money use.",
    }
    return result


def save_signals(signals: List[Dict[str, object]], output_path: str = "latest_signals.csv") -> None:
    path = Path(output_path)
    df = pd.DataFrame(signals)
    df.to_csv(path, index=False)
    path.with_suffix(".json").write_text(json.dumps(signals, indent=2), encoding="utf-8")


def load_latest_signals(path: str = "latest_signals.csv") -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def format_signal_table(signals: List[Dict[str, object]]) -> str:
    lines = []
    for s in signals:
        lines.append(
            f"{s['symbol']} | {s['action']} | strength {s['signal_strength_pct']}% | "
            f"price {s['last_price']} | SL {s['stop_loss']} | TP {s['take_profit']} | "
            f"session {s['session_quality']}"
        )
    return "\n".join(lines)


def send_email_alert(signals: List[Dict[str, object]], force: bool = False) -> bool:
    """Send an email alert if EMAIL_ENABLED=true and at least one tradable signal exists."""
    if not env_bool("EMAIL_ENABLED", False):
        print("EMAIL_ENABLED is false. Email skipped.")
        return False

    tradable = [s for s in signals if s.get("action") in {"BUY", "SELL"}]
    if not tradable and not force:
        print("No BUY/SELL signal. Email skipped.")
        return False

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    email_to = os.getenv("EMAIL_TO", smtp_user)

    if not smtp_user or not smtp_password or not email_to:
        raise RuntimeError("SMTP_USER, SMTP_PASSWORD, and EMAIL_TO must be set for email alerts.")

    msg = EmailMessage()
    msg["Subject"] = "Forex AI Signal Alert"
    msg["From"] = smtp_user
    msg["To"] = email_to
    body = (
        "Forex AI Signal Bot alert\n\n"
        + format_signal_table(tradable if tradable else signals)
        + "\n\nRisk reminder: this is educational, not financial advice. Use demo first."
    )
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
    print(f"Email sent to {email_to}")
    return True


def oanda_request(method: str, path: str, data: Optional[dict] = None) -> dict:
    token = os.getenv("OANDA_API_TOKEN", "")
    if not token:
        raise RuntimeError("OANDA_API_TOKEN is missing.")

    env = os.getenv("OANDA_ENV", "practice").strip().lower()
    if env == "live":
        base = "https://api-fxtrade.oanda.com"
    else:
        base = "https://api-fxpractice.oanda.com"

    url = base + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept-Datetime-Format": "RFC3339",
    }
    response = requests.request(method, url, headers=headers, json=data, timeout=30)
    if not response.ok:
        raise RuntimeError(f"OANDA error {response.status_code}: {response.text}")
    return response.json() if response.text else {}


def close_oanda_opposite_position(signal: Dict[str, object]) -> Optional[dict]:
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("OANDA_ACCOUNT_ID is missing.")
    instrument = symbol_for_oanda(str(signal["symbol"]))
    action = signal.get("action")

    if action == "BUY":
        data = {"shortUnits": "ALL"}
    elif action == "SELL":
        data = {"longUnits": "ALL"}
    else:
        return None

    try:
        return oanda_request("PUT", f"/v3/accounts/{account_id}/positions/{instrument}/close", data=data)
    except RuntimeError as exc:
        # No opposite position can produce a broker error. Print and continue.
        print(f"Opposite-position close skipped/failed: {exc}")
        return None



def get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def safe_json(value: object) -> str:
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def trade_journal_path() -> Path:
    return Path(os.getenv("TRADE_JOURNAL_FILE", "trade_journal.csv"))


def risk_state_path() -> Path:
    return Path(os.getenv("RISK_STATE_FILE", "risk_state.json"))


def append_trade_journal(event: Dict[str, object]) -> None:
    """Append an execution/safety event to a local CSV journal."""
    path = trade_journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event_type": event.get("event_type", "execution"),
        "broker": event.get("broker", ""),
        "symbol": event.get("symbol", ""),
        "action": event.get("action", ""),
        "status": event.get("status", ""),
        "reason": event.get("reason", ""),
        "signal_strength": event.get("signal_strength", ""),
        "entry": event.get("entry", ""),
        "stop_loss": event.get("stop_loss", ""),
        "take_profit": event.get("take_profit", ""),
        "units": event.get("units", ""),
        "nav": event.get("nav", ""),
        "daily_start_nav": event.get("daily_start_nav", ""),
        "daily_loss_pct": event.get("daily_loss_pct", ""),
        "spread_pips": event.get("spread_pips", ""),
        "checks": event.get("checks", ""),
        "response": event.get("response", ""),
    }
    # Keep extra fields if caller supplied any.
    for key, value in event.items():
        row.setdefault(key, value)

    for key, value in list(row.items()):
        if isinstance(value, (dict, list, tuple)):
            row[key] = safe_json(value)

    new_row = pd.DataFrame([row])
    if path.exists() and path.stat().st_size > 0:
        try:
            old = pd.read_csv(path)
            combined = pd.concat([old, new_row], ignore_index=True, sort=False)
        except Exception:
            combined = new_row
    else:
        combined = new_row
    combined.to_csv(path, index=False)


def load_trade_journal() -> pd.DataFrame:
    path = trade_journal_path()
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def successful_trade_count_today(symbol: Optional[str] = None) -> int:
    df = load_trade_journal()
    if df.empty or "timestamp_utc" not in df.columns:
        return 0
    ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mask = ts.dt.strftime("%Y-%m-%d") == today
    if "status" in df.columns:
        mask &= df["status"].astype(str).str.lower().isin({"sent", "filled", "order_sent"})
    if "event_type" in df.columns:
        mask &= df["event_type"].astype(str).str.lower().isin({"execution", "trade"})
    if symbol and "symbol" in df.columns:
        clean = normalize_symbol(symbol)
        mask &= df["symbol"].astype(str).map(normalize_symbol) == clean
    return int(mask.fillna(False).sum())


def last_successful_trade_time(symbol: Optional[str] = None) -> Optional[datetime]:
    df = load_trade_journal()
    if df.empty or "timestamp_utc" not in df.columns:
        return None
    mask = pd.Series(True, index=df.index)
    if "status" in df.columns:
        mask &= df["status"].astype(str).str.lower().isin({"sent", "filled", "order_sent"})
    if "event_type" in df.columns:
        mask &= df["event_type"].astype(str).str.lower().isin({"execution", "trade"})
    if symbol and "symbol" in df.columns:
        clean = normalize_symbol(symbol)
        mask &= df["symbol"].astype(str).map(normalize_symbol) == clean
    ts = pd.to_datetime(df.loc[mask, "timestamp_utc"], utc=True, errors="coerce").dropna()
    if ts.empty:
        return None
    return ts.max().to_pydatetime()


def load_risk_state() -> Dict[str, object]:
    path = risk_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_risk_state(state: Dict[str, object]) -> None:
    path = risk_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def oanda_account_summary() -> Dict[str, object]:
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("OANDA_ACCOUNT_ID is missing.")
    response = oanda_request("GET", f"/v3/accounts/{account_id}/summary")
    account = response.get("account", {})
    nav = float(account.get("NAV", account.get("nav", account.get("balance", 0))))
    balance = float(account.get("balance", nav))
    unrealized_pl = float(account.get("unrealizedPL", 0))
    return {"nav": nav, "balance": balance, "unrealized_pl": unrealized_pl, "raw": account}


def oanda_open_trades_count() -> int:
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("OANDA_ACCOUNT_ID is missing.")
    response = oanda_request("GET", f"/v3/accounts/{account_id}/openTrades")
    return int(len(response.get("trades", [])))


def pip_size(symbol: str) -> float:
    clean = normalize_symbol(symbol)
    if "JPY" in clean:
        return 0.01
    if clean == "XAUUSD":
        return 0.10
    return 0.0001


def oanda_spread_pips(symbol: str) -> float:
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("OANDA_ACCOUNT_ID is missing.")
    instrument = symbol_for_oanda(symbol)
    response = oanda_request("GET", f"/v3/accounts/{account_id}/pricing?instruments={instrument}")
    prices = response.get("prices", [])
    if not prices:
        raise RuntimeError(f"No OANDA pricing returned for {instrument}")
    price = prices[0]
    bid = float(price["bids"][0]["price"])
    ask = float(price["asks"][0]["price"])
    return abs(ask - bid) / pip_size(symbol)


def check_daily_loss_limit(nav: float) -> Dict[str, object]:
    """Track UTC daily starting NAV and block if daily loss limit is reached."""
    max_daily_loss_pct = get_env_float("MAX_DAILY_LOSS_PCT", 2.0)
    max_intraday_drawdown_pct = get_env_float("MAX_INTRADAY_DRAWDOWN_PCT", 0.0)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state = load_risk_state()

    if state.get("date") != today or not state.get("daily_start_nav"):
        state = {"date": today, "daily_start_nav": float(nav), "peak_nav": float(nav)}
    else:
        state["peak_nav"] = max(float(state.get("peak_nav", nav)), float(nav))

    start_nav = float(state.get("daily_start_nav", nav))
    peak_nav = float(state.get("peak_nav", nav))
    daily_loss_pct = 0.0 if start_nav <= 0 else max(0.0, (start_nav - nav) / start_nav * 100)
    drawdown_pct = 0.0 if peak_nav <= 0 else max(0.0, (peak_nav - nav) / peak_nav * 100)

    state["last_nav"] = float(nav)
    state["daily_loss_pct"] = daily_loss_pct
    state["intraday_drawdown_pct"] = drawdown_pct
    save_risk_state(state)

    if max_daily_loss_pct > 0 and daily_loss_pct >= max_daily_loss_pct:
        return {
            "ok": False,
            "reason": f"Daily loss limit hit: {daily_loss_pct:.2f}% >= {max_daily_loss_pct:.2f}%",
            "daily_start_nav": start_nav,
            "daily_loss_pct": daily_loss_pct,
        }
    if max_intraday_drawdown_pct > 0 and drawdown_pct >= max_intraday_drawdown_pct:
        return {
            "ok": False,
            "reason": f"Intraday drawdown limit hit: {drawdown_pct:.2f}% >= {max_intraday_drawdown_pct:.2f}%",
            "daily_start_nav": start_nav,
            "daily_loss_pct": daily_loss_pct,
        }
    return {
        "ok": True,
        "reason": "Daily loss check passed",
        "daily_start_nav": start_nav,
        "daily_loss_pct": daily_loss_pct,
    }


def signal_currencies(symbol: str) -> List[str]:
    clean = normalize_symbol(symbol)
    if clean == "XAUUSD":
        return ["XAU", "USD"]
    if len(clean) >= 6:
        return [clean[:3], clean[3:6]]
    return [clean]


def news_blackout_check(signal: Dict[str, object]) -> Dict[str, object]:
    """
    Optional free news safety filter using a CSV file.

    NEWS_BLACKOUT_FILE format option A:
        time_utc,currency,impact,event
        2026-06-23T12:30:00Z,USD,High,CPI

    Option B:
        start_utc,end_utc,currency,impact,event
        2026-06-23T12:00:00Z,2026-06-23T13:15:00Z,USD,High,FOMC
    """
    if not env_bool("NEWS_FILTER_ENABLED", False):
        return {"ok": True, "reason": "News filter disabled"}

    path = Path(os.getenv("NEWS_BLACKOUT_FILE", "news_blackout.csv"))
    strict = env_bool("NEWS_FILTER_STRICT", True)
    if not path.exists():
        if strict:
            return {"ok": False, "reason": f"News filter strict mode: {path} is missing"}
        return {"ok": True, "reason": "News file missing; strict mode disabled"}

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {"ok": False, "reason": f"Could not read news file: {exc}"}

    if df.empty:
        return {"ok": True, "reason": "News file empty"}

    now = datetime.now(timezone.utc)
    currencies = set(signal_currencies(str(signal.get("symbol", ""))))
    impact_allow = {x.strip().lower() for x in os.getenv("NEWS_BLOCK_IMPACTS", "High").split(",") if x.strip()}
    window_minutes = get_env_int("NEWS_BLACKOUT_MINUTES", 45)

    for _, row in df.iterrows():
        currency = str(row.get("currency", "")).upper().strip()
        if currency and currency not in currencies:
            continue
        impact = str(row.get("impact", "High")).lower().strip()
        if impact_allow and impact not in impact_allow:
            continue

        if "start_utc" in df.columns and "end_utc" in df.columns and pd.notna(row.get("start_utc")):
            start = pd.to_datetime(row.get("start_utc"), utc=True, errors="coerce")
            end = pd.to_datetime(row.get("end_utc"), utc=True, errors="coerce")
        else:
            event_time = pd.to_datetime(row.get("time_utc"), utc=True, errors="coerce")
            if pd.isna(event_time):
                continue
            start = event_time - pd.Timedelta(minutes=window_minutes)
            end = event_time + pd.Timedelta(minutes=window_minutes)

        if pd.isna(start) or pd.isna(end):
            continue
        if start.to_pydatetime() <= now <= end.to_pydatetime():
            event = str(row.get("event", "news event"))
            return {"ok": False, "reason": f"News blackout active for {currency}: {event}"}

    return {"ok": True, "reason": "No matching news blackout"}


def estimated_risk_per_unit_usd(symbol: str, entry: float, stop_loss: float) -> Optional[float]:
    """Approximate USD risk per 1 unit for common USD pairs."""
    clean = normalize_symbol(symbol)
    distance = abs(float(entry) - float(stop_loss))
    if distance <= 0:
        return None
    if clean == "XAUUSD":
        return distance  # rough: 1 unit = 1 oz
    if len(clean) != 6:
        return None
    base, quote = clean[:3], clean[3:]
    if quote == "USD":
        return distance
    if base == "USD" and entry > 0:
        return distance / float(entry)
    # Cross pairs need a conversion price; fallback to fixed units.
    return None


def calculate_oanda_units(signal: Dict[str, object], nav: Optional[float] = None) -> int:
    fixed_units = abs(get_env_int("OANDA_UNITS", 1000))
    max_units = abs(get_env_int("MAX_UNITS", fixed_units))
    min_units = abs(get_env_int("MIN_UNITS", 1))

    if not env_bool("USE_RISK_POSITION_SIZING", False):
        return int(max(min_units, min(fixed_units, max_units)))

    try:
        entry = float(signal.get("entry") or signal.get("last_price"))
        stop_loss = float(signal.get("stop_loss"))
    except (TypeError, ValueError):
        return int(max(min_units, min(fixed_units, max_units)))

    if nav is None:
        try:
            nav = float(oanda_account_summary()["nav"])
        except Exception:
            nav = None
    if not nav or nav <= 0:
        return int(max(min_units, min(fixed_units, max_units)))

    risk_pct = get_env_float("RISK_PER_TRADE_PCT", 0.5)
    risk_amount = float(nav) * max(0.0, risk_pct) / 100.0
    risk_per_unit = estimated_risk_per_unit_usd(str(signal.get("symbol", "")), entry, stop_loss)
    if not risk_per_unit or risk_per_unit <= 0 or risk_amount <= 0:
        return int(max(min_units, min(fixed_units, max_units)))

    units = int(math.floor(risk_amount / risk_per_unit))
    return int(max(min_units, min(units, max_units)))


def add_check(checks: List[Dict[str, object]], ok: bool, name: str, message: str) -> bool:
    checks.append({"name": name, "ok": bool(ok), "message": message})
    return bool(ok)


def pre_trade_risk_check(signal: Dict[str, object], broker: str = "oanda") -> Dict[str, object]:
    """Run live-trading safety checks before any broker order is sent."""
    checks: List[Dict[str, object]] = []
    approved = True
    nav: Optional[float] = None
    daily_start_nav: Optional[float] = None
    daily_loss_pct: Optional[float] = None
    spread_pips: Optional[float] = None

    symbol = normalize_symbol(str(signal.get("symbol", "")))
    action = str(signal.get("action", "")).upper()
    strength = float(signal.get("signal_strength", 0) or 0)

    mode = os.getenv("AUTO_TRADE_MODE", "signal_only").strip().lower()
    approved &= add_check(checks, mode == "auto", "auto_trade_mode", "AUTO_TRADE_MODE must be auto")

    if os.getenv("OANDA_ENV", "practice").strip().lower() == "live":
        live_ok = env_bool("LIVE_TRADING_ENABLED", False) and os.getenv("LIVE_ACCOUNT_CONFIRMATION", "") == "I_ACCEPT_LIVE_RISK_2026"
        approved &= add_check(
            checks,
            live_ok,
            "live_confirmation",
            "Live OANDA requires LIVE_TRADING_ENABLED=true and LIVE_ACCOUNT_CONFIRMATION=I_ACCEPT_LIVE_RISK_2026",
        )

    approved &= add_check(checks, action in {"BUY", "SELL"}, "action", "Signal action must be BUY or SELL")

    min_exec_strength = get_env_float("EXECUTION_MIN_SIGNAL_STRENGTH", get_env_float("MIN_SIGNAL_STRENGTH", 0.62))
    approved &= add_check(
        checks,
        strength >= min_exec_strength,
        "signal_strength",
        f"Signal strength {strength:.3f} must be >= {min_exec_strength:.3f}",
    )

    allowed_raw = os.getenv("ALLOWED_LIVE_SYMBOLS", os.getenv("SYMBOLS", ""))
    allowed = {normalize_symbol(x.strip()) for x in allowed_raw.split(",") if x.strip()}
    if allowed:
        approved &= add_check(checks, symbol in allowed, "allowed_symbol", f"{symbol} must be in allowed symbol list")

    approved &= add_check(checks, market_open_now(), "market_open", "FX market must be open")

    if env_bool("BLOCK_LOW_QUALITY_SESSIONS", True):
        session_quality = str(signal.get("session_quality", "")).upper()
        approved &= add_check(
            checks,
            session_quality not in {"LOW", ""},
            "session_quality",
            f"Session quality is {session_quality}; LOW sessions are blocked",
        )

    if env_bool("REQUIRE_STOP_LOSS", True):
        approved &= add_check(checks, bool(signal.get("stop_loss")), "stop_loss", "Stop loss is required")
    if env_bool("REQUIRE_TAKE_PROFIT", True):
        approved &= add_check(checks, bool(signal.get("take_profit")), "take_profit", "Take profit is required")

    max_trades_day = get_env_int("MAX_TRADES_PER_DAY", 3)
    if max_trades_day > 0:
        count = successful_trade_count_today()
        approved &= add_check(
            checks,
            count < max_trades_day,
            "max_trades_per_day",
            f"Trades today {count}/{max_trades_day}",
        )

    max_symbol_trades_day = get_env_int("MAX_TRADES_PER_SYMBOL_PER_DAY", 1)
    if max_symbol_trades_day > 0:
        count_symbol = successful_trade_count_today(symbol)
        approved &= add_check(
            checks,
            count_symbol < max_symbol_trades_day,
            "max_trades_per_symbol_per_day",
            f"{symbol} trades today {count_symbol}/{max_symbol_trades_day}",
        )

    cooldown_minutes = get_env_int("COOLDOWN_MINUTES", 60)
    if cooldown_minutes > 0:
        last_time = last_successful_trade_time(symbol)
        if last_time:
            minutes_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 60.0
            approved &= add_check(
                checks,
                minutes_since >= cooldown_minutes,
                "cooldown",
                f"Minutes since last {symbol} trade: {minutes_since:.1f}/{cooldown_minutes}",
            )
        else:
            add_check(checks, True, "cooldown", "No previous trade for symbol today")

    news_check = news_blackout_check(signal)
    approved &= add_check(checks, bool(news_check["ok"]), "news_filter", str(news_check["reason"]))

    if broker.lower() == "oanda":
        strict_account = env_bool("ACCOUNT_RISK_STRICT", True)
        try:
            summary = oanda_account_summary()
            nav = float(summary["nav"])
            loss_check = check_daily_loss_limit(nav)
            daily_start_nav = float(loss_check.get("daily_start_nav", nav))
            daily_loss_pct = float(loss_check.get("daily_loss_pct", 0.0))
            approved &= add_check(checks, bool(loss_check["ok"]), "daily_loss", str(loss_check["reason"]))
        except Exception as exc:
            ok = not strict_account
            approved &= add_check(checks, ok, "daily_loss", f"Could not verify account NAV: {exc}")

        max_open = get_env_int("MAX_OPEN_TRADES", 2)
        if max_open > 0:
            try:
                open_count = oanda_open_trades_count()
                approved &= add_check(checks, open_count < max_open, "max_open_trades", f"Open trades {open_count}/{max_open}")
            except Exception as exc:
                approved &= add_check(checks, not strict_account, "max_open_trades", f"Could not verify open trades: {exc}")

        if env_bool("SPREAD_FILTER_ENABLED", True):
            try:
                spread_pips = float(oanda_spread_pips(symbol))
                max_spread = get_env_float("MAX_SPREAD_PIPS", 2.5)
                approved &= add_check(checks, spread_pips <= max_spread, "spread", f"Spread {spread_pips:.2f}/{max_spread:.2f} pips")
            except Exception as exc:
                approved &= add_check(checks, not strict_account, "spread", f"Could not verify spread: {exc}")

    reason = "; ".join([c["message"] for c in checks if not c["ok"]]) or "All safety checks passed"
    return {
        "approved": bool(approved),
        "reason": reason,
        "checks": checks,
        "nav": nav,
        "daily_start_nav": daily_start_nav,
        "daily_loss_pct": daily_loss_pct,
        "spread_pips": spread_pips,
    }


def execute_oanda_signal(signal: Dict[str, object]) -> Dict[str, object]:
    """
    Place an OANDA market order with SL/TP after safety checks.

    Extra live-safety guards added:
    - AUTO_TRADE_MODE=auto is required
    - Daily loss limit
    - Max trades per day/symbol
    - Cooldown between trades
    - Max open trades
    - Spread filter
    - Optional news blackout CSV
    - Extra live-account confirmation
    - Optional risk-percent position sizing
    """
    execution_enabled = env_bool("TRADE_EXECUTION_ENABLED", False) or env_bool("LIVE_TRADING_ENABLED", False)
    if not execution_enabled:
        result = {"status": "skipped", "reason": "TRADE_EXECUTION_ENABLED/LIVE_TRADING_ENABLED is false"}
        append_trade_journal({**result, "broker": "oanda", "symbol": signal.get("symbol", ""), "action": signal.get("action", "")})
        return result
    if os.getenv("I_UNDERSTAND_TRADING_RISK", "no").strip().lower() != "yes":
        result = {"status": "skipped", "reason": "I_UNDERSTAND_TRADING_RISK is not yes"}
        append_trade_journal({**result, "broker": "oanda", "symbol": signal.get("symbol", ""), "action": signal.get("action", "")})
        return result
    if signal.get("action") not in {"BUY", "SELL"}:
        result = {"status": "skipped", "reason": "Signal is not BUY/SELL"}
        append_trade_journal({**result, "broker": "oanda", "symbol": signal.get("symbol", ""), "action": signal.get("action", "")})
        return result

    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("OANDA_ACCOUNT_ID is missing.")

    safety = pre_trade_risk_check(signal, broker="oanda")
    journal_base = {
        "broker": "oanda",
        "symbol": signal.get("symbol", ""),
        "action": signal.get("action", ""),
        "signal_strength": signal.get("signal_strength", ""),
        "entry": signal.get("entry", ""),
        "stop_loss": signal.get("stop_loss", ""),
        "take_profit": signal.get("take_profit", ""),
        "nav": safety.get("nav", ""),
        "daily_start_nav": safety.get("daily_start_nav", ""),
        "daily_loss_pct": safety.get("daily_loss_pct", ""),
        "spread_pips": safety.get("spread_pips", ""),
        "checks": safety.get("checks", []),
    }
    if not safety["approved"]:
        result = {"status": "blocked", "reason": safety["reason"], "checks": safety["checks"]}
        append_trade_journal({**journal_base, **result})
        return result

    instrument = symbol_for_oanda(str(signal["symbol"]))
    units_abs = calculate_oanda_units(signal, nav=safety.get("nav"))
    units = units_abs if signal["action"] == "BUY" else -units_abs

    if env_bool("CLOSE_OPPOSITE_POSITIONS", True):
        close_oanda_opposite_position(signal)

    order = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
        }
    }

    if signal.get("stop_loss"):
        order["order"]["stopLossOnFill"] = {"price": str(signal["stop_loss"])}
    if signal.get("take_profit"):
        order["order"]["takeProfitOnFill"] = {"price": str(signal["take_profit"])}

    try:
        response = oanda_request("POST", f"/v3/accounts/{account_id}/orders", data=order)
        result = {"status": "sent", "broker": "oanda", "instrument": instrument, "units": units, "response": response}
        append_trade_journal({**journal_base, **result})
        return result
    except Exception as exc:
        result = {"status": "error", "reason": str(exc), "broker": "oanda", "instrument": instrument, "units": units}
        append_trade_journal({**journal_base, **result})
        raise


def scan_symbols(
    symbols: Iterable[str],
    period: str = "180d",
    timeframe: str = "1h",
    min_strength: float = 0.62,
    output_path: str = "latest_signals.csv",
    email: bool = False,
    execute: bool = False,
) -> List[Dict[str, object]]:
    """Analyze many symbols, save files, optionally email and execute."""
    signals: List[Dict[str, object]] = []
    for symbol in symbols:
        try:
            signal = analyze_symbol(symbol, period=period, timeframe=timeframe, min_strength=min_strength)
            signals.append(signal)
            print(
                f"{signal['symbol']}: {signal['action']} "
                f"strength={signal['signal_strength_pct']}% price={signal['last_price']}"
            )
        except Exception as exc:  # keep scanning other pairs
            print(f"ERROR analyzing {symbol}: {exc}")
            signals.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "symbol": normalize_symbol(symbol),
                    "action": "ERROR",
                    "signal_strength": 0,
                    "signal_strength_pct": 0,
                    "reason": str(exc),
                }
            )

    save_signals(signals, output_path=output_path)

    if email:
        send_email_alert(signals)

    if execute:
        for signal in signals:
            if signal.get("action") in {"BUY", "SELL"}:
                try:
                    print(execute_oanda_signal(signal))
                except Exception as exc:
                    print(f"Execution error for {signal.get('symbol')}: {exc}")

    return signals


def signals_from_env() -> List[str]:
    raw = os.getenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD")
    return [normalize_symbol(x.strip()) for x in raw.split(",") if x.strip()]


def bridge_line(signal: Dict[str, object]) -> str:
    """
    Simple plain-text format for MetaTrader EA polling:
    SYMBOL|ACTION|STRENGTH|ENTRY|SL|TP|TIMESTAMP
    """
    fields = [
        signal.get("symbol", ""),
        signal.get("action", "WAIT"),
        signal.get("signal_strength", 0),
        signal.get("entry", ""),
        signal.get("stop_loss", ""),
        signal.get("take_profit", ""),
        signal.get("timestamp_utc", ""),
    ]
    return "|".join("" if v is None else str(v) for v in fields)


def run_loop_from_env() -> None:
    symbols = signals_from_env()
    period = os.getenv("PERIOD", "180d")
    timeframe = os.getenv("TIMEFRAME", "1h")
    output_path = os.getenv("SIGNAL_OUTPUT", "latest_signals.csv")
    min_strength = float(os.getenv("MIN_SIGNAL_STRENGTH", "0.62"))
    interval_seconds = int(os.getenv("LOOP_INTERVAL_SECONDS", "900"))
    email_enabled = env_bool("EMAIL_ENABLED", False)
    execute_enabled = env_bool("TRADE_EXECUTION_ENABLED", False) or env_bool("LIVE_TRADING_ENABLED", False)

    print("Starting Forex AI Signal Bot loop")
    print(f"Symbols={symbols}, timeframe={timeframe}, every {interval_seconds}s")
    while True:
        print("\n--- Scan started", datetime.now(timezone.utc).isoformat(timespec="seconds"), "---")
        scan_symbols(
            symbols=symbols,
            period=period,
            timeframe=timeframe,
            min_strength=min_strength,
            output_path=output_path,
            email=email_enabled,
            execute=execute_enabled,
        )
        print(f"Sleeping {interval_seconds} seconds...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    scan_symbols(
        symbols=signals_from_env(),
        period=os.getenv("PERIOD", "180d"),
        timeframe=os.getenv("TIMEFRAME", "1h"),
        min_strength=float(os.getenv("MIN_SIGNAL_STRENGTH", "0.62")),
        output_path=os.getenv("SIGNAL_OUTPUT", "latest_signals.csv"),
        email=env_bool("EMAIL_ENABLED", False),
        execute=env_bool("TRADE_EXECUTION_ENABLED", False) or env_bool("LIVE_TRADING_ENABLED", False),
    )
