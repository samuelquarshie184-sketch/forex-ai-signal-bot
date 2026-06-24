"""
Simple educational backtest for the Forex AI Signal Bot.

This is a quick sanity check, not a professional-grade backtester. It uses the
same features and a train/test split, then simulates next-candle direction.
"""

from __future__ import annotations

import argparse
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from forex_ai_bot import (
    FEATURE_COLUMNS,
    add_features,
    fetch_yahoo_ohlc,
    normalize_symbol,
    technical_score,
)


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def backtest_symbol(
    symbol: str,
    period: str = "180d",
    timeframe: str = "1h",
    min_strength: float = 0.62,
    starting_equity: float = 10000.0,
    risk_fraction: float = 1.0,
) -> Dict[str, object]:
    """Train on early data, test on later data, and return simple performance stats."""
    symbol = normalize_symbol(symbol)
    df = add_features(fetch_yahoo_ohlc(symbol, period=period, interval=timeframe)).dropna(subset=FEATURE_COLUMNS + ["target", "future_return"])
    if len(df) < 200 or df["target"].nunique() < 2:
        return {"symbol": symbol, "error": "Not enough data"}

    split = int(len(df) * 0.7)
    train = df.iloc[:split].copy()
    test = df.iloc[split:].copy()

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["target"].astype(int))

    prob_up = model.predict_proba(test[FEATURE_COLUMNS])[:, list(model.classes_).index(1)]
    tech_prob_up = test.apply(lambda row: (technical_score(row) + 1) / 2, axis=1).values
    hybrid_prob_up = 0.65 * prob_up + 0.35 * tech_prob_up

    direction = np.zeros(len(test))
    direction[hybrid_prob_up >= min_strength] = 1
    direction[hybrid_prob_up <= (1 - min_strength)] = -1

    trades = test.copy()
    trades["direction"] = direction
    trades = trades[trades["direction"] != 0].copy()
    if trades.empty:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "trades": 0,
            "win_rate": None,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "model_accuracy": float(accuracy_score(test["target"].astype(int), model.predict(test[FEATURE_COLUMNS]))),
        }

    # Simple next-candle return. This ignores intrabar stop-loss/take-profit, slippage,
    # financing, and broker-specific spreads. Use it only as a learning filter.
    trades["strategy_return"] = trades["direction"] * trades["future_return"] * risk_fraction
    trades["win"] = trades["strategy_return"] > 0
    trades["equity"] = starting_equity * (1 + trades["strategy_return"]).cumprod()

    total_return = trades["equity"].iloc[-1] / starting_equity - 1
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "period": period,
        "min_strength": min_strength,
        "bars": int(len(df)),
        "test_bars": int(len(test)),
        "trades": int(len(trades)),
        "win_rate": round(float(trades["win"].mean()), 4),
        "avg_trade_return_pct": round(float(trades["strategy_return"].mean() * 100), 4),
        "total_return_pct": round(float(total_return * 100), 2),
        "max_drawdown_pct": round(float(max_drawdown(trades["equity"]) * 100), 2),
        "model_accuracy": round(float(accuracy_score(test["target"].astype(int), model.predict(test[FEATURE_COLUMNS]))), 4),
    }


def run_backtest(symbols: Iterable[str], period: str, timeframe: str, min_strength: float, output: str) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for symbol in symbols:
        try:
            row = backtest_symbol(symbol, period=period, timeframe=timeframe, min_strength=min_strength)
        except Exception as exc:
            row = {"symbol": normalize_symbol(symbol), "error": str(exc)}
        rows.append(row)
        print(row)
    report = pd.DataFrame(rows)
    report.to_csv(output, index=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="EURUSD,GBPUSD,USDJPY")
    parser.add_argument("--period", default="180d")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--min-strength", type=float, default=0.62)
    parser.add_argument("--output", default="backtest_report.csv")
    args = parser.parse_args()

    symbols = [normalize_symbol(x.strip()) for x in args.symbols.split(",") if x.strip()]
    run_backtest(symbols, args.period, args.timeframe, args.min_strength, args.output)


if __name__ == "__main__":
    main()
