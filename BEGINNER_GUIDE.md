# Beginner Guide: Build Your Forex AI Signal Bot Step by Step

This guide explains the whole system like you are brand new.

## 0. Safety first

Forex trading is risky. An AI bot can lose money. No bot is always right. This project is for learning and demo testing first.

**Rules for beginners:**

1. Use a demo account first.
2. Never start with big lot sizes.
3. Never remove the stop loss.
4. Never use martingale/grid recovery while learning.
5. Never put API passwords in public GitHub.
6. If you do not understand a trade, do not allow the bot to place it.

---

## 1. What the system does, in simple words

Think of the bot like a small trading team:

1. **Eyes** = gets price data.
2. **Brain** = uses indicators + machine learning to decide if price may go up or down.
3. **Score board** = dashboard shows BUY, SELL, or WAIT and signal strength.
4. **Messenger** = sends email alerts.
5. **Hand** = optional broker connector places and closes trades.

The safest first version is: **Eyes + Brain + Dashboard + Email**. Add the trading hand only after demo testing.

---

## 2. Free tools you need

| Tool | Why you need it | Free? |
|---|---|---|
| Google account | Google Colab + Gmail | Yes |
| Google Colab | Run Python notebooks in browser | Free with limits |
| GitHub account | Store project files for deployment | Free |
| Streamlit Community Cloud | Deploy dashboard website | Free tier |
| Gmail App Password | Send email alerts | Free with Gmail/2FA |
| OANDA demo/practice account | Demo broker API execution | Free demo |
| MetaTrader 4/5 demo account | MT4/MT5 testing | Free demo |

**Truth:** you cannot remove all manual work. You must manually create accounts, copy API keys, and connect your broker. After setup, scanning and alerts can be automated.

---

## 3. Understand the signal

The signal has:

- `action`: BUY, SELL, WAIT, ERROR
- `signal_strength_pct`: how strong the bot thinks the signal is
- `ai_prob_up`: machine-learning probability that next candle moves up
- `technical_score`: old-school indicator score from EMA, MACD, RSI
- `entry`: current/estimated entry price
- `stop_loss`: price where trade should close if wrong
- `take_profit`: price where trade should close if right
- `session_quality`: whether the current trading session has good liquidity

Example:

```text
EURUSD | BUY | strength 68.4% | price 1.08500 | SL 1.08050 | TP 1.09175 | session HIGH
```

This means: the bot sees a possible EURUSD buy. It is not a guarantee.

---

## 4. Process One: Run signals in Google Colab

### Step 4.1: Put the project in Colab

Beginner method:

1. Download the folder `forex_ai_signal_bot`.
2. Open Google Drive.
3. Upload the folder.
4. Open Google Colab.
5. Mount Drive in Colab.

In Colab:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Then go to your folder:

```python
%cd /content/drive/MyDrive/forex_ai_signal_bot
```

### Step 4.2: Install packages

```python
!pip install -r requirements.txt
```

### Step 4.3: Run first signal scan

```python
!python forex_ai_bot.py
```

Then view results:

```python
import pandas as pd
pd.read_csv('latest_signals.csv')
```

If you see a table, your bot brain is working.

---

## 5. Process Two: Send live email signals

### Step 5.1: Create Gmail App Password

1. Open your Google Account.
2. Turn on 2-Step Verification.
3. Create an App Password for Mail.
4. Copy the 16-character password.

### Step 5.2: Set email details in Colab

Do not type passwords directly into shared notebooks. Use `getpass`:

```python
import os, getpass
os.environ['EMAIL_ENABLED'] = 'true'
os.environ['SMTP_HOST'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '465'
os.environ['SMTP_USER'] = input('Your Gmail: ')
os.environ['SMTP_PASSWORD'] = getpass.getpass('Gmail app password: ')
os.environ['EMAIL_TO'] = input('Where should alerts go? ')
```

### Step 5.3: Run scan with email

```python
from forex_ai_bot import scan_symbols
scan_symbols(['EURUSD','GBPUSD','USDJPY'], timeframe='1h', period='180d', email=True)
```

The bot emails only when it finds BUY/SELL signals unless forced.

---

## 6. Process Three: Run a repeated live loop in Colab

```python
!python run_colab_signal_loop.py --loop --interval 900
```

This scans every 900 seconds = 15 minutes.

**Important:** Colab can disconnect. This is fine for learning, but not safe for serious 24/5 execution.

---

## 7. Process Four: Start the dashboard

### Option A: Run dashboard in Colab for testing

```python
!streamlit run dashboard.py --server.port 8501 &
```

You need a tunnel to view it from Colab. A common free method is localtunnel:

```python
!npm install -g localtunnel
!lt --port 8501
```

Open the URL it gives you.

### Option B: Deploy dashboard free on Streamlit Community Cloud

1. Create a GitHub account.
2. Create a new repository, for example `forex-ai-signal-bot`.
3. Upload all files in this folder.
4. Go to Streamlit Community Cloud.
5. Click **New app**.
6. Choose your GitHub repo.
7. Main file path: `dashboard.py`.
8. Deploy.

Now you have a dashboard website.

---

## 8. Process Five: Demo trading with OANDA API

This is the easiest broker-style execution from Python/Colab because it uses REST API.

### Step 8.1: Create OANDA practice account

1. Create an OANDA demo/practice account.
2. Create API token.
3. Copy account ID.

### Step 8.2: Set broker environment variables

```python
import os, getpass
os.environ['TRADE_EXECUTION_ENABLED'] = 'true'
os.environ['AUTO_TRADE_MODE'] = 'auto'
os.environ['I_UNDERSTAND_TRADING_RISK'] = 'yes'
os.environ['OANDA_ENV'] = 'practice'
os.environ['OANDA_API_TOKEN'] = getpass.getpass('OANDA practice token: ')
os.environ['OANDA_ACCOUNT_ID'] = input('OANDA practice account ID: ')
os.environ['OANDA_UNITS'] = '1000'  # very small demo size
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

### Step 8.3: Execute from signals

```python
from forex_ai_bot import scan_symbols
scan_symbols(['EURUSD'], timeframe='1h', period='180d', email=False, execute=True)
```

The code can:

- open a BUY/SELL market order
- attach stop loss
- attach take profit
- close the opposite position before opening a new one
- block trades if safety rules fail
- save decisions to `trade_journal.csv`
- track daily loss in `risk_state.json`

Keep this in demo until you have strong proof. Also read `LIVE_TRADING_SAFETY_GUIDE.md` before any real account connection.

---

## 9. Process Six: Connect MetaTrader 4/5

Google Colab cannot directly control your MT4/MT5 desktop terminal because MT4/MT5 runs on your PC/VPS, not inside Colab. So we use a bridge:

1. Python bot creates latest signal.
2. FastAPI bridge exposes it as a URL.
3. MT4/MT5 Expert Advisor reads the URL.
4. EA places or closes trades in MetaTrader.

### Step 9.1: Start the API bridge locally

```bash
uvicorn api_bridge:app --host 0.0.0.0 --port 8000
```

Then test:

```text
http://127.0.0.1:8000/latest.txt?symbol=EURUSD
```

You should see something like:

```text
EURUSD|BUY|0.68|1.085|1.081|1.091|2026-06-23T...
```

### Step 9.2: Deploy bridge online

Free beginner options change often, but common choices are:

- Render web service
- Railway trial/free credits if available
- Fly.io free allowance if available
- PythonAnywhere for simple apps
- Oracle Cloud Free Tier VM if you can set it up

For Render-style setup:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api_bridge:app --host 0.0.0.0 --port $PORT`
- Environment variables: `SYMBOLS`, `TIMEFRAME`, `PERIOD`, `API_SHARED_SECRET`

### Step 9.3: Install MT5 EA

1. Open MetaTrader 5.
2. Open **File > Open Data Folder**.
3. Go to `MQL5/Experts`.
4. Copy `metatrader/MQL5_ForexAI_Bridge_EA.mq5` there.
5. Open MetaEditor.
6. Compile the EA.
7. In MT5: **Tools > Options > Expert Advisors**.
8. Tick **Allow algorithmic trading**.
9. Tick **Allow WebRequest for listed URL** and add your bridge domain, for example:
   `https://your-bridge.onrender.com`
10. Attach EA to EURUSD chart.
11. Keep `AllowNewTrades=false` first and watch logs.
12. When demo-tested, set `AllowNewTrades=true`.

### Step 9.4: Install MT4 EA

Same idea, but copy `metatrader/MQL4_ForexAI_Bridge_EA.mq4` into `MQL4/Experts`.

---

## 10. Recommended beginner settings

| Setting | Beginner value |
|---|---|
| Pairs | EURUSD, GBPUSD, USDJPY only |
| Timeframe | 1h |
| Minimum signal strength | 0.62 to 0.70 |
| Lot size | 0.01 demo |
| OANDA units | 1000 demo |
| Stop loss | Always ON |
| Take profit | Always ON |
| Close opposite trades | Yes |
| Real money | No, not at beginner stage |

---

## 11. How to improve later

After the starter version works, improve it like this:

1. Replace Yahoo data with broker data.
2. Add spread filter from broker.
3. Add news filter so it avoids high-impact news.
4. Add walk-forward backtesting.
5. Add max daily loss lock.
6. Add trade journal and performance dashboard.
7. Add model retraining schedule.
8. Add Telegram/WhatsApp alerts if needed.
9. Add VPS for 24/5 reliability.

---

## 12. Very important final truth

A professional trading bot is not just code. It needs:

- testing
- risk control
- broker connection testing
- error handling
- monitoring
- legal/compliance awareness if selling signals
- stable hosting

This starter kit gives you the base. The correct journey is:

**Signals only → email alerts → dashboard → demo execution → long testing → only then consider live.**
