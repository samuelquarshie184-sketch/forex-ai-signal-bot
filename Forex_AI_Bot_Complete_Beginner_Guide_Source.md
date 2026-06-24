# Complete Beginner's Guide for the Forex AI Signal + Trading Bot

**Project package:** `forex_ai_signal_bot.zip`  
**Main beginner notebook:** `FOREX_AI_BOT_COLAB.ipynb`  
**Important:** This is educational software. It is not financial advice and it does not guarantee profit.

## The simple truth

The bot can help you scan the Forex market, create signals, show a dashboard, send email alerts, and connect to demo/live trading through OANDA or MetaTrader bridge. But every trading bot can lose money. Start with demo. Use small risk. Never trade money you cannot afford to lose.

## The safest journey

Signals only -> Backtest -> Dashboard -> Email alerts -> Demo auto-trading -> Review journal -> Improve settings -> Small live testing only after proof.

## What the bot does

1. Gets price data.
2. Creates indicators like EMA, MACD, RSI, ATR.
3. Trains a small machine-learning model.
4. Combines AI probability with technical analysis.
5. Produces BUY, SELL, or WAIT.
6. Shows signal strength, entry, stop loss, take profit, and trading session.
7. Can email signals.
8. Can optionally place trades through broker connections.

## Main files

- `FOREX_AI_BOT_COLAB.ipynb` - beginner notebook for Google Colab.
- `forex_ai_bot.py` - main bot engine.
- `dashboard.py` - Streamlit dashboard.
- `backtest.py` - simple train/test backtest.
- `run_colab_signal_loop.py` - repeated scanner.
- `api_bridge.py` - bridge API for MetaTrader.
- `metatrader/MQL4_ForexAI_Bridge_EA.mq4` - MT4 EA.
- `metatrader/MQL5_ForexAI_Bridge_EA.mq5` - MT5 EA.
- `LIVE_TRADING_SAFETY_GUIDE.md` - safety guide.
- `.env.example` - settings template.

## Use Google Colab only

You do not need to install Python locally. Colab already has Python. Upload the project folder to Google Drive, open the notebook, mount Drive, install requirements, and run the cells.

## Colab steps

1. Download `forex_ai_signal_bot.zip`.
2. Unzip it.
3. Upload `forex_ai_signal_bot/` to Google Drive.
4. Open `FOREX_AI_BOT_COLAB.ipynb` in Google Colab.
5. Run:

```python
from google.colab import drive
drive.mount('/content/drive')
%cd /content/drive/MyDrive/forex_ai_signal_bot
!pip install -r requirements.txt
```

6. Run first scan:

```python
from forex_ai_bot import scan_symbols
signals = scan_symbols(['EURUSD','GBPUSD','USDJPY'], timeframe='1h', period='180d')
```

## Backtesting

Run before trading:

```python
!python backtest.py --symbols EURUSD,GBPUSD,USDJPY --period 180d --timeframe 1h --min-strength 0.62
```

Open:

```python
import pandas as pd
pd.read_csv('backtest_report.csv')
```

## Email alerts

Use Gmail App Password and set environment variables:

```python
import os, getpass
os.environ['EMAIL_ENABLED'] = 'true'
os.environ['SMTP_USER'] = input('Your Gmail: ')
os.environ['SMTP_PASSWORD'] = getpass.getpass('Gmail app password: ')
os.environ['EMAIL_TO'] = input('Receiver email: ')
```

Then run scan with `email=True`.

## OANDA demo execution

Use demo/practice first:

```python
import os, getpass
os.environ['TRADE_EXECUTION_ENABLED'] = 'true'
os.environ['AUTO_TRADE_MODE'] = 'auto'
os.environ['I_UNDERSTAND_TRADING_RISK'] = 'yes'
os.environ['OANDA_ENV'] = 'practice'
os.environ['OANDA_API_TOKEN'] = getpass.getpass('OANDA practice token: ')
os.environ['OANDA_ACCOUNT_ID'] = input('OANDA account ID: ')
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

Then:

```python
from forex_ai_bot import scan_symbols
scan_symbols(['EURUSD','GBPUSD','USDJPY'], timeframe='1h', period='180d', execute=True)
```

## Real live trading

Only after stable demo results. OANDA live requires:

```python
os.environ['LIVE_TRADING_ENABLED'] = 'true'
os.environ['LIVE_ACCOUNT_CONFIRMATION'] = 'I_ACCEPT_LIVE_RISK_2026'
os.environ['OANDA_ENV'] = 'live'
```

Start tiny. Risk 0.5% to 1% maximum per trade.

## MetaTrader

MetaTrader needs the desktop terminal or VPS. Copy the EA into MetaTrader Experts folder, allow WebRequest, attach EA to a chart, keep `AllowNewTrades=false` first, then demo test.

## Safety

Use daily loss limit, max trades per day, cooldown, spread filter, required stop loss/take profit, optional news filter, and journal review.

## Journal

After execution, read:

```python
import pandas as pd
pd.read_csv('trade_journal.csv')
```

Look at `status`, `reason`, `checks`, `nav`, `daily_loss_pct`, and `spread_pips`.

## Final beginner rule

Do not chase fast money. Your first goal is to learn, protect your account, collect data, and improve slowly.
