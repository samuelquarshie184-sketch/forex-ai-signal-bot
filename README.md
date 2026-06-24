# Forex AI Signal + Trading Bot Starter Kit

Educational starter project for a live-looking Forex AI signal dashboard, email alerts, and optional broker execution.

> **Important:** This is not financial advice and not a profit guarantee. Forex and CFDs are risky. Keep broker execution OFF until you have tested on a demo account for a long time.

## What is included

| File | Purpose |
|---|---|
| `forex_ai_bot.py` | Main AI signal engine: downloads data, creates indicators, trains a quick ML model, creates BUY/SELL/WAIT signals, email alerts, OANDA practice execution. |
| `dashboard.py` | Streamlit dashboard showing signal strength, best signal, trading sessions, signal table, and charts. |
| `run_colab_signal_loop.py` | Run one scan or a repeating scan loop in Google Colab. |
| `api_bridge.py` | FastAPI bridge that serves latest signals to MetaTrader EAs. |
| `backtest.py` | Simple train/test backtest before live trading. |
| `metatrader/MQL5_ForexAI_Bridge_EA.mq5` | MT5 Expert Advisor bridge. |
| `metatrader/MQL4_ForexAI_Bridge_EA.mq4` | MT4 Expert Advisor bridge. |
| `.env.example` | Settings template. Do not share your real `.env`. |
| `LIVE_TRADING_SAFETY_GUIDE.md` | Safety settings for demo/live execution. |
| `Forex_AI_Bot_Complete_Beginner_Guide.pdf` | Detailed downloadable PDF setup guide. |
| `Forex_AI_Bot_Complete_Setup_Guide_Step_By_Step.pdf` | Same detailed step-by-step PDF guide with explicit name. |
| `Forex_AI_Bot_Complete_Setup_Guide_Source.md` | Editable source version of the detailed guide. |
| `news_blackout.example.csv` | Example high-impact-news blackout file. |
| `FOREX_AI_BOT_COLAB.ipynb` | Beginner Colab notebook. |
| `BEGINNER_GUIDE.md` | Step-by-step beginner guide. |

## Quick start in Google Colab

1. Upload this folder to Google Drive or GitHub.
2. Open `FOREX_AI_BOT_COLAB.ipynb` in Google Colab.
3. Run the cells from top to bottom.
4. Start with **signals only**. Do not enable broker execution yet.

## Quick start locally

```bash
cd forex_ai_signal_bot
python -m pip install -r requirements.txt
python forex_ai_bot.py
python backtest.py --symbols EURUSD,GBPUSD,USDJPY --period 180d --timeframe 1h
streamlit run dashboard.py
```

## Free tools used

- Google Colab: learning, training, and running short signal loops.
- GitHub: store code and deploy from repository.
- Streamlit Community Cloud: free dashboard deployment.
- Gmail SMTP/App Password: free email alerts if you already have Gmail.
- OANDA Practice API: demo trading execution via REST API.
- MetaTrader 4/5: execution through the included bridge EA on your own PC/VPS.

## Live-trading safety

Broker execution remains OFF by default. To trade even on demo, the upgraded safety system requires `TRADE_EXECUTION_ENABLED=true`, `AUTO_TRADE_MODE=auto`, and `I_UNDERSTAND_TRADING_RISK=yes`.

Real OANDA live mode additionally requires `LIVE_TRADING_ENABLED=true` and `LIVE_ACCOUNT_CONFIRMATION=I_ACCEPT_LIVE_RISK_2026`.

Read `LIVE_TRADING_SAFETY_GUIDE.md` before connecting any real account.

## Honest limitation

Google Colab is not a true 24/7 production server. It can disconnect. Use it to learn and test. For 24/5 trading, use a local machine that stays on or a VPS.
