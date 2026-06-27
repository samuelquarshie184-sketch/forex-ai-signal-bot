"""
Scheduled signal/email runner for GitHub Actions or any hosted cron worker.

It scans the selected pairs and sends an email after each scheduled update.
Secrets must be provided by the hosting platform as environment variables.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import requests

from forex_ai_bot import scan_symbols, send_email_alert, signals_from_env


def main() -> None:
    symbols = signals_from_env()
    timeframe = os.getenv("TIMEFRAME", "1h")
    period = os.getenv("PERIOD", "180d")
    min_strength = float(os.getenv("MIN_SIGNAL_STRENGTH", "0.65"))
    output_path = os.getenv("SIGNAL_OUTPUT", "latest_signals.csv")
    force_email = os.getenv("EMAIL_FORCE_SEND", "true").strip().lower() in {"1", "true", "yes", "on"}

    print("=" * 70)
    print("Forex AI scheduled signal/email update")
    print("Time UTC:", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print("Symbols:", symbols)
    print("Timeframe:", timeframe)
    print("Period:", period)
    print("Minimum strength:", min_strength)
    print("Output:", output_path)
    print("Force email:", force_email)
    print("=" * 70)

    signals = scan_symbols(
        symbols=symbols,
        timeframe=timeframe,
        period=period,
        min_strength=min_strength,
        output_path=output_path,
        email=False,
        execute=False,
    )
    bridge_base_url = os.getenv("BRIDGE_BASE_URL", "").rstrip("/")
    bridge_secret = os.getenv("API_SHARED_SECRET", "")

    if bridge_base_url and bridge_secret:
        try:
            push_url = f"{bridge_base_url}/push?secret={bridge_secret}"
            response = requests.post(push_url, json=signals, timeout=60)
            print("Bridge push status:", response.status_code)
            print(response.text[:1000])
            response.raise_for_status()
        except Exception as exc:
            print("WARNING: Could not push signals to Render bridge:", repr(exc))
    else:
        print("Bridge push skipped because BRIDGE_BASE_URL or API_SHARED_SECRET is missing.")
    print(pd.DataFrame(signals).to_string(index=False))

    # For a scheduled update, users asked for email after every update.
    send_email_alert(signals, force=force_email)

    print("Scheduled update complete.")


if __name__ == "__main__":
    main()
