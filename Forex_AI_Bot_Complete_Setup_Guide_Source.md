# Forex AI Signal + Trading Bot — Complete Step-by-Step Beginner Setup Guide

This guide is written so you can follow the whole process one step at a time, mainly using **Google Colab**. You do **not** need to install Python on your computer for the OANDA/Colab route.

> **Important risk warning:** This bot can help you scan the market, create signals, send alerts, and test auto-trading. It cannot guarantee profit. Forex trading can lose real money. Start with demo.

---

## 1. What you are building

You are building a Forex AI assistant that can:

1. Download Forex price data.
2. Create technical indicators such as EMA, MACD, RSI, and ATR.
3. Train a quick AI/machine-learning model.
4. Produce **BUY**, **SELL**, or **WAIT** signals.
5. Show signal strength.
6. Show stop-loss and take-profit suggestions.
7. Show trading sessions and best time/session quality.
8. Send signal alerts by email.
9. Run a dashboard.
10. Optionally place demo/live trades through OANDA.
11. Optionally connect to MT4/MT5 through the Expert Advisor bridge.

Your beginner path should be:

```text
Signals only
→ Backtest
→ Dashboard
→ Email alerts
→ OANDA practice/demo
→ Review journal
→ Improve settings
→ Tiny live only after long demo proof
```

---

## 2. Files inside the package

After downloading and unzipping `forex_ai_signal_bot.zip`, you will see:

| File/folder | Purpose |
|---|---|
| `FOREX_AI_BOT_COLAB.ipynb` | Main Google Colab notebook. Start here. |
| `forex_ai_bot.py` | Main AI signal, email, OANDA, and safety engine. |
| `dashboard.py` | Streamlit dashboard. |
| `backtest.py` | Simple historical backtest. |
| `run_colab_signal_loop.py` | Repeated signal scanner. |
| `api_bridge.py` | API bridge for MT4/MT5. |
| `requirements.txt` | Python packages to install in Colab. |
| `.env.example` | Example settings file. Do not put secrets in public repos. |
| `LIVE_TRADING_SAFETY_GUIDE.md` | Extra safety guide. |
| `news_blackout.example.csv` | Example news blackout file. |
| `metatrader/` | MT4/MT5 EA files and setup guide. |

---

## 3. Accounts/tools you need

| Tool/account | Why you need it | Needed now? |
|---|---|---|
| Google account | Google Drive and Colab | Yes |
| Google Drive | Store your bot folder | Yes |
| Google Colab | Run Python in browser | Yes |
| Gmail App Password | Email alerts | Optional |
| OANDA practice account | Demo broker API trading | Recommended |
| GitHub | Deploy dashboard/API later | Optional |
| Streamlit Community Cloud | Free dashboard deployment | Optional |
| MT4/MT5 broker demo | MetaTrader testing | Optional |
| VPS/cloud server | More stable 24/5 operation later | Later |

---

## 4. Download and upload to Google Drive

1. Download `forex_ai_signal_bot.zip` from the workspace.
2. Unzip it on your computer.
3. You should now see a folder named `forex_ai_signal_bot`.
4. Open Google Drive.
5. Upload the whole `forex_ai_signal_bot` folder to **My Drive**.
6. Wait until upload finishes.
7. Open the folder and confirm these files exist:
   - `FOREX_AI_BOT_COLAB.ipynb`
   - `forex_ai_bot.py`
   - `requirements.txt`
   - `dashboard.py`
   - `backtest.py`

---

## 5. Open the notebook in Google Colab

1. In Google Drive, open the `forex_ai_signal_bot` folder.
2. Double-click `FOREX_AI_BOT_COLAB.ipynb`.
3. Choose **Open with Google Colaboratory**.
4. If Colab is not available, click **Connect more apps** and search for Colaboratory.

---

## 6. Mount Google Drive in Colab

Run this inside Colab:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Google will ask for permission. Allow it.

---

## 7. Move into the bot folder

If you uploaded the folder directly into My Drive, run:

```python
%cd /content/drive/MyDrive/forex_ai_signal_bot
```

If you uploaded it inside another folder, adjust the path. Example:

```python
%cd /content/drive/MyDrive/TradingBots/forex_ai_signal_bot
```

Check files:

```python
!ls
```

You should see `forex_ai_bot.py`, `requirements.txt`, `dashboard.py`, and `backtest.py`.

---

## 8. Install packages in Colab

Run:

```python
!pip install -r requirements.txt
```

This installs the required packages inside Colab. You are not installing Python on your computer.

---

## 9. Run your first signal scan

Run:

```python
from forex_ai_bot import scan_symbols

signals = scan_symbols(
    ['EURUSD', 'GBPUSD', 'USDJPY'],
    timeframe='1h',
    period='180d',
    output_path='latest_signals.csv'
)
```

Then view results:

```python
import pandas as pd
pd.read_csv('latest_signals.csv')
```

If you see rows with EURUSD, GBPUSD, and USDJPY, the bot is working.

---

## 10. Understand the signal table

| Column | Meaning | Beginner advice |
|---|---|---|
| `symbol` | Forex pair | Start with majors only |
| `action` | BUY, SELL, WAIT, ERROR | Respect WAIT |
| `signal_strength_pct` | Signal strength | Use 65%+ for execution testing |
| `hybrid_prob_up` | Combined AI + technical probability | Not a guarantee |
| `ai_prob_up` | AI probability only | Not enough alone |
| `technical_score` | EMA/MACD/RSI score | Positive bullish, negative bearish |
| `entry` | Suggested/current entry | Broker price may differ |
| `stop_loss` | Loss protection | Never trade without it |
| `take_profit` | Profit target | Helps avoid emotional exits |
| `risk_reward` | Reward compared with risk | Higher than 1 is better |
| `session_quality` | Trading session quality | Avoid LOW as beginner |
| `reason` | Why signal happened | Always read it |

---

## 11. Run backtest before trading

Run:

```python
!python backtest.py --symbols EURUSD,GBPUSD,USDJPY --period 180d --timeframe 1h --min-strength 0.62
```

View:

```python
import pandas as pd
pd.read_csv('backtest_report.csv')
```

Read these columns:

| Column | Meaning |
|---|---|
| `trades` | Number of simulated trades |
| `win_rate` | Percentage of wins |
| `total_return_pct` | Simplified return |
| `max_drawdown_pct` | Worst drop from peak |
| `model_accuracy` | Direction accuracy |

If backtest looks poor, do **not** trade live.

---

## 12. Run dashboard in Colab

Start Streamlit:

```python
!streamlit run dashboard.py --server.port 8501 > /content/streamlit.log 2>&1 &
```

Create tunnel:

```python
!npm install -g localtunnel
!lt --port 8501
```

Open the URL it gives you.

The dashboard shows:

- Best signal
- Signal table
- Signal strength gauges
- Price chart
- Trading session quality
- Safety/journal section

---

## 13. Deploy dashboard free with GitHub + Streamlit

1. Create a GitHub account.
2. Create a new repository called `forex-ai-signal-bot`.
3. Upload the project files.
4. Do **not** upload private `.env` or API keys.
5. Open Streamlit Community Cloud.
6. Connect GitHub.
7. Click **New app**.
8. Choose your repo.
9. Main file path: `dashboard.py`.
10. Deploy.

Optional environment settings:

```text
SYMBOLS=EURUSD,GBPUSD,USDJPY
TIMEFRAME=1h
PERIOD=180d
MIN_SIGNAL_STRENGTH=0.62
```

---

## 14. Email signal alerts

Create Gmail App Password:

1. Open Google Account.
2. Go to Security.
3. Turn on 2-Step Verification.
4. Search for App Passwords.
5. Create one for Mail.
6. Copy the 16-character password.

Set email variables in Colab:

```python
import os, getpass

os.environ['EMAIL_ENABLED'] = 'true'
os.environ['SMTP_HOST'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '465'
os.environ['SMTP_USER'] = input('Your Gmail: ')
os.environ['SMTP_PASSWORD'] = getpass.getpass('Gmail app password: ')
os.environ['EMAIL_TO'] = input('Send alerts to: ')
```

Run scan with email:

```python
from forex_ai_bot import scan_symbols
scan_symbols(['EURUSD','GBPUSD','USDJPY'], timeframe='1h', period='180d', email=True)
```

---

## 15. Repeated live signal loop in Colab

Run:

```python
!python run_colab_signal_loop.py --loop --interval 900
```

900 seconds = 15 minutes.

Important: Colab can disconnect. For learning this is okay. For serious 24/5 trading later, use VPS/cloud/broker hosting.

---

## 16. OANDA practice auto-trading

Create OANDA practice account:

1. Open OANDA.
2. Create demo/practice account.
3. Generate API token.
4. Copy account ID.
5. Keep token private.

Set safe demo variables:

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
os.environ['CLOSE_OPPOSITE_POSITIONS'] = 'true'
```

Run demo execution:

```python
from forex_ai_bot import scan_symbols

scan_symbols(
    ['EURUSD','GBPUSD','USDJPY'],
    timeframe='1h',
    period='180d',
    execute=True
)
```

Possible results:

| Status | Meaning |
|---|---|
| `sent` | Order request was sent |
| `blocked` | Safety rule stopped it |
| `skipped` | Execution not enabled or not confirmed |
| `error` | Broker/API problem |

---

## 17. Safety controls

| Setting | Beginner value | Purpose |
|---|---|---|
| `AUTO_TRADE_MODE` | `signal_only` first, `auto` for demo | Master mode |
| `EXECUTION_MIN_SIGNAL_STRENGTH` | `0.65` | Blocks weak trades |
| `MAX_DAILY_LOSS_PCT` | `2.0` | Stops after daily loss |
| `MAX_TRADES_PER_DAY` | `3` | Prevents overtrading |
| `MAX_TRADES_PER_SYMBOL_PER_DAY` | `1` | Prevents revenge trading |
| `MAX_OPEN_TRADES` | `2` | Limits open exposure |
| `COOLDOWN_MINUTES` | `60` | Wait before another trade |
| `MAX_SPREAD_PIPS` | `2.5` | Avoid bad spreads |
| `REQUIRE_STOP_LOSS` | `true` | Blocks trades without SL |
| `REQUIRE_TAKE_PROFIT` | `true` | Blocks trades without TP |

Do not reduce safety limits just to get more trades.

---

## 18. News filter

Create `news_blackout.csv`:

```csv
time_utc,currency,impact,event
2026-06-23T12:30:00Z,USD,High,CPI release
2026-06-24T18:00:00Z,USD,High,FOMC rate decision
```

Enable it:

```python
import os
os.environ['NEWS_FILTER_ENABLED'] = 'true'
os.environ['NEWS_FILTER_STRICT'] = 'true'
os.environ['NEWS_BLACKOUT_FILE'] = 'news_blackout.csv'
os.environ['NEWS_BLACKOUT_MINUTES'] = '45'
os.environ['NEWS_BLOCK_IMPACTS'] = 'High'
```

---

## 19. Read trade journal and risk state

Trade journal:

```python
import pandas as pd
pd.read_csv('trade_journal.csv')
```

Important columns:

- `status`
- `reason`
- `checks`
- `symbol`
- `action`
- `signal_strength`
- `nav`
- `daily_loss_pct`
- `spread_pips`
- `response`

Risk state:

```python
print(open('risk_state.json').read())
```

---

## 20. OANDA live mode later

Only after stable demo results:

```python
import os, getpass

os.environ['TRADE_EXECUTION_ENABLED'] = 'true'
os.environ['AUTO_TRADE_MODE'] = 'auto'
os.environ['LIVE_TRADING_ENABLED'] = 'true'
os.environ['LIVE_ACCOUNT_CONFIRMATION'] = 'I_ACCEPT_LIVE_RISK_2026'
os.environ['I_UNDERSTAND_TRADING_RISK'] = 'yes'
os.environ['OANDA_ENV'] = 'live'
os.environ['OANDA_API_TOKEN'] = getpass.getpass('OANDA LIVE token: ')
os.environ['OANDA_ACCOUNT_ID'] = input('OANDA LIVE account ID: ')
os.environ['OANDA_UNITS'] = '100'
os.environ['MAX_UNITS'] = '100'
```

Start tiny. Your first live goal is checking safety, not making fast money.

---

## 21. MT4/MT5 bridge setup

MetaTrader usually needs a PC or VPS. Colab cannot directly control your desktop terminal. The bridge works like this:

```text
Python/API bridge -> latest.txt signal URL -> MT4/MT5 EA -> broker trade
```

Run bridge locally:

```bash
uvicorn api_bridge:app --host 0.0.0.0 --port 8000
```

Test:

```text
http://127.0.0.1:8000/latest.txt?symbol=EURUSD
```

MT5 setup:

1. Open MetaTrader 5.
2. File > Open Data Folder.
3. Open `MQL5/Experts`.
4. Copy `MQL5_ForexAI_Bridge_EA.mq5` there.
5. Open MetaEditor and compile.
6. Tools > Options > Expert Advisors.
7. Enable Algo Trading and WebRequest.
8. Add your bridge base URL.
9. Attach EA to EURUSD chart.
10. Set `SignalURL`.
11. Keep `AllowNewTrades=false` first.
12. Demo test before live.

MT4 setup is similar, but use `MQL4/Experts` and `MQL4_ForexAI_Bridge_EA.mq4`.

---

## 22. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| File not found | Wrong Colab folder | Run `!ls` and `%cd` correctly |
| No module named... | Packages not installed | Run `!pip install -r requirements.txt` |
| No data returned | Symbol/free data issue | Try EURUSD, 1h, 180d |
| Email fails | Wrong Gmail setup | Use App Password |
| OANDA unauthorized | Wrong token/account/env | Check practice vs live |
| Trade blocked | Safety rule failed | Read `trade_journal.csv` |
| Dashboard not opening | Tunnel stopped | Restart Streamlit/localtunnel |
| Colab disconnected | Runtime limit | Restart; use VPS later |
| MT WebRequest failed | URL not allowed | Add base URL in MT options |

---

## 23. Final checklist

Before first signal:

- [ ] Downloaded ZIP.
- [ ] Uploaded folder to Google Drive.
- [ ] Opened Colab notebook.
- [ ] Mounted Drive.
- [ ] Changed into correct folder.
- [ ] Installed requirements.
- [ ] Ran first signal scan.

Before demo auto-trading:

- [ ] Ran backtest.
- [ ] Understood signal columns.
- [ ] Created OANDA practice account.
- [ ] Set OANDA_ENV=practice.
- [ ] Set safety variables.
- [ ] Read trade journal.

Before any live trading:

- [ ] Demo-tested for long enough.
- [ ] Understood that losses can happen.
- [ ] Know how to stop the bot.
- [ ] Start with tiny size only.
- [ ] Keep stop loss and safety rules on.

**Final rule:** If you do not understand a step, stop and ask before continuing.
