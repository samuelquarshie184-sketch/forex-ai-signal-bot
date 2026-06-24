# Forex AI Bot Deployment Guide

This guide moves the project away from Google Colab for a more reliable setup.

## Recommended beginner deployment

Use two free/simple services first:

1. **Streamlit Community Cloud** for the dashboard.
2. **GitHub Actions scheduled workflow** for signal scans and email alerts.

This does not require your laptop or Colab to remain open.

> Important: free services can sleep, delay scheduled jobs, or have limits. For serious 24/5 automatic trading, use a VPS.

---

## Part A — GitHub upload

1. Create a GitHub account.
2. Create a new repository, for example `forex-ai-signal-bot`.
3. Upload the contents of the `forex_ai_signal_bot` folder.
4. Do **not** upload `.env` or private passwords/tokens.

Make sure these files are in the repository root:

- `forex_ai_bot.py`
- `dashboard.py`
- `requirements.txt`
- `github_actions_signal_email.py`
- `.github/workflows/signal_email.yml`

---

## Part B — Add GitHub variables and secrets

Open your GitHub repository.

Go to:

`Settings → Secrets and variables → Actions`

### Add repository variables

Click **Variables** and add:

| Name | Value |
|---|---|
| `SYMBOLS` | `GBPUSD,EURUSD` |
| `TIMEFRAME` | `1h` |
| `PERIOD` | `180d` |
| `MIN_SIGNAL_STRENGTH` | `0.65` |
| `EMAIL_FORCE_SEND` | `true` |

### Add repository secrets

Click **Secrets** and add:

| Name | Value |
|---|---|
| `SMTP_USER` | your Gmail address |
| `SMTP_PASSWORD` | Gmail App Password, not normal password |
| `EMAIL_TO` | email address to receive alerts |

Never put these secrets directly into code.

---

## Part C — Test GitHub Actions email updater

Open your repository.

Go to:

`Actions → Forex AI signal email update → Run workflow`

Click **Run workflow**.

Open the running job logs and confirm you see:

- pair scan output
- `Email sent to ...`

The workflow also runs automatically every 15 minutes, although GitHub may delay scheduled jobs sometimes.

---

## Part D — Deploy dashboard to Streamlit Community Cloud

1. Go to `https://share.streamlit.io` or Streamlit Community Cloud.
2. Sign in with GitHub.
3. Click **New app**.
4. Choose your repository.
5. Branch: `main`.
6. Main file path: `dashboard.py`.
7. Click **Deploy**.

### Add Streamlit secrets/settings

In the Streamlit app settings, add secrets:

```toml
SYMBOLS = "GBPUSD,EURUSD"
TIMEFRAME = "1h"
PERIOD = "180d"
MIN_SIGNAL_STRENGTH = "0.65"
SIGNAL_OUTPUT = "latest_signals.csv"
```

The dashboard can scan live when opened. If it sleeps, refresh the app.

---

## Part E — Optional API bridge deployment

The API bridge is needed later for MT5 EA automatic trading.

You can deploy `api_bridge.py` on Render using `render.yaml`.

Start command:

```bash
uvicorn api_bridge:app --host 0.0.0.0 --port $PORT
```

Test endpoints:

```text
https://YOUR-APP.onrender.com/scan?secret=YOUR_SECRET
https://YOUR-APP.onrender.com/latest.txt?symbol=GBPUSD&secret=YOUR_SECRET
```

Free Render services may sleep. For MT5 auto-trading, a VPS or paid always-on service is better.

---

## Part F — Real automatic trading later

For MT5 automatic trading you need:

- MT5 desktop or Windows VPS
- `metatrader/MQL5_ForexAI_Bridge_EA.mq5`
- a public API bridge URL
- MT5 WebRequest permission
- demo testing first

Do not connect live money until demo results are stable.
