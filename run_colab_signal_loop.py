"""Run the Forex AI signal scan once or in a repeated Colab loop."""

import argparse
import os
from datetime import datetime, timezone

from forex_ai_bot import env_bool, scan_symbols, signals_from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="Forex AI Signal Bot runner")
    parser.add_argument("--loop", action="store_true", help="Keep scanning repeatedly")
    parser.add_argument("--interval", type=int, default=int(os.getenv("LOOP_INTERVAL_SECONDS", "900")), help="Loop seconds")
    parser.add_argument("--no-email", action="store_true", help="Do not send email")
    parser.add_argument("--execute", action="store_true", help="Attempt broker execution if env guards allow it")
    args = parser.parse_args()

    symbols = signals_from_env()
    period = os.getenv("PERIOD", "180d")
    timeframe = os.getenv("TIMEFRAME", "1h")
    output_path = os.getenv("SIGNAL_OUTPUT", "latest_signals.csv")
    min_strength = float(os.getenv("MIN_SIGNAL_STRENGTH", "0.62"))

    def run_once():
        print("\nScan time:", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        return scan_symbols(
            symbols=symbols,
            period=period,
            timeframe=timeframe,
            min_strength=min_strength,
            output_path=output_path,
            email=(env_bool("EMAIL_ENABLED", False) and not args.no_email),
            execute=args.execute,
        )

    if args.loop:
        import time

        while True:
            run_once()
            print(f"Sleeping {args.interval} seconds. Colab may still disconnect when Google limits the session.")
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
