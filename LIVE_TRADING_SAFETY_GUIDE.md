# Live Trading Safety Upgrade

This upgrade makes the bot more live-ready, but it still does **not** guarantee profit. It adds guardrails so the bot can refuse dangerous trades.

## New safety features added

| Safety feature | What it does |
|---|---|
| `AUTO_TRADE_MODE` | Must be `auto` before broker orders are allowed. Default is `signal_only`. |
| Live confirmation | Real OANDA live mode requires `LIVE_ACCOUNT_CONFIRMATION=I_ACCEPT_LIVE_RISK_2026`. |
| Minimum execution strength | Blocks weak signals before execution. |
| Stop-loss required | Blocks trades with no stop loss. |
| Take-profit required | Blocks trades with no take profit. |
| Daily loss limit | Stops new trades if account NAV drops too much in one UTC day. |
| Intraday drawdown limit | Stops new trades if account falls from the day’s peak too much. |
| Max trades per day | Prevents overtrading. |
| Max trades per symbol per day | Prevents repeated revenge trades on one pair. |
| Max open trades | Prevents too many simultaneous positions. |
| Cooldown minutes | Waits before taking another trade on the same pair. |
| Spread filter | Blocks trades when spread is too high. |
| Optional news blackout | Blocks trades around high-impact news if you provide a news CSV. |
| Trade journal | Saves every sent, blocked, skipped, or error decision to `trade_journal.csv`. |
| Risk state | Saves daily starting NAV and drawdown state to `risk_state.json`. |
| Optional risk sizing | Can size OANDA units from account risk percentage. |

---

## Safe demo auto-trading settings

Use this first:

```python
import os, getpass

os.environ['TRADE_EXECUTION_ENABLED'] = 'true'
os.environ['AUTO_TRADE_MODE'] = 'auto'
os.environ['I_UNDERSTAND_TRADING_RISK'] = 'yes'
os.environ['OANDA_ENV'] = 'practice'
os.environ['OANDA_API_TOKEN'] = getpass.getpass('OANDA practice API token: ')
os.environ['OANDA_ACCOUNT_ID'] = input('OANDA practice account ID: ')
os.environ['OANDA_UNITS'] = '1000'
os.environ['MAX_UNITS'] = '1000'
os.environ['EXECUTION_MIN_SIGNAL_STRENGTH'] = '0.65'
os.environ['MAX_DAILY_LOSS_PCT'] = '2.0'
os.environ['MAX_TRADES_PER_DAY'] = '3'
os.environ['MAX_TRADES_PER_SYMBOL_PER_DAY'] = '1'
os.environ['MAX_OPEN_TRADES'] = '2'
os.environ['COOLDOWN_MINUTES'] = '60'
os.environ['MAX_SPREAD_PIPS'] = '2.5'
```

Then run:

```python
from forex_ai_bot import scan_symbols
scan_symbols(['EURUSD','GBPUSD','USDJPY'], timeframe='1h', period='180d', execute=True)
```

If the safety system blocks a trade, that is good. It means it is protecting the account.

---

## Real OANDA live mode

Only after long demo testing, live mode needs extra confirmation:

```python
os.environ['TRADE_EXECUTION_ENABLED'] = 'true'
os.environ['AUTO_TRADE_MODE'] = 'auto'
os.environ['LIVE_TRADING_ENABLED'] = 'true'
os.environ['LIVE_ACCOUNT_CONFIRMATION'] = 'I_ACCEPT_LIVE_RISK_2026'
os.environ['I_UNDERSTAND_TRADING_RISK'] = 'yes'
os.environ['OANDA_ENV'] = 'live'
os.environ['OANDA_API_TOKEN'] = getpass.getpass('OANDA LIVE token: ')
os.environ['OANDA_ACCOUNT_ID'] = input('OANDA LIVE account ID: ')
```

Do not do this until the bot has performed well on demo.

---

## Optional risk-percent sizing

Fixed units is safer for beginners. Later, you can use risk-percent sizing:

```python
os.environ['USE_RISK_POSITION_SIZING'] = 'true'
os.environ['RISK_PER_TRADE_PCT'] = '0.5'
os.environ['MAX_UNITS'] = '2000'
```

This tries to size trades so the stop-loss risk is about 0.5% of account NAV. It is approximate and works best for major USD pairs.

---

## Optional news blackout file

Create a file named `news_blackout.csv`:

```csv
time_utc,currency,impact,event
2026-06-23T12:30:00Z,USD,High,CPI
2026-06-24T18:00:00Z,USD,High,FOMC rate decision
```

Then enable:

```python
os.environ['NEWS_FILTER_ENABLED'] = 'true'
os.environ['NEWS_FILTER_STRICT'] = 'true'
os.environ['NEWS_BLACKOUT_MINUTES'] = '45'
```

The bot will block trades for affected currency pairs from 45 minutes before to 45 minutes after the event.

---

## Reading the trade journal

After execution attempts:

```python
import pandas as pd
pd.read_csv('trade_journal.csv')
```

Look at:

- `status`: `sent`, `blocked`, `skipped`, or `error`
- `reason`: why it was blocked/skipped
- `checks`: full safety checklist
- `nav`, `daily_loss_pct`, `spread_pips`

---

## Beginner live-money rule

If you ever go live, start tiny:

- 0.01 lots on MT4/MT5, or
- 100 to 1000 OANDA units, and
- max 0.5% to 1% risk per trade.

Your first live goal is **survival and learning**, not fast money.
