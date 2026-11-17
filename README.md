# 🤖 AI Weekly Email & Calendar Report Agent

An AI-powered agent that automatically processes your Gmail inbox every **Friday at 12:00 PM (noon)** in your configured timezone. It filters out promotions, newsletters, and non-actionable emails, then generates:

1. **Executive summary** of the week.
2. **Prioritized To-Do List** (🔴 High, 🟡 Medium, 🟢 Low) with direct links to the original emails.
3. **Deadline & event detection** with one-click Google Calendar links and assisted confirmation.
4. **Weekly HTML report** sent directly to your inbox.

---

## 📂 Project Structure

```
email-agent/
├── agent.py                 # Main CLI (run, auth, list-events, confirm)
├── config.py                # Settings: timezone, paths, OAuth scopes
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template (copy → .env)
├── credentials.json         # ⚠️  NOT included — you must generate this (see Step 1)
├── token.json               # ⚠️  Auto-generated after first login — do not share
├── services/
│   ├── gmail_service.py     # Smart inbox reader & email sender
│   ├── calendar_service.py  # One-click links & Google Calendar scheduling
│   └── ai_analyzer.py       # AI brain (Google Gemini, model cascade)
├── templates/
│   └── report_email.html    # Responsive HTML email template
└── .github/
    └── workflows/
        └── weekly_report.yml  # GitHub Actions scheduler (recommended)
```

> **Important — files never committed:**
> `credentials.json`, `token.json`, `.env`, `pending_events.json`, `*.log`
> These are listed in `.gitignore` to prevent accidental secret leakage.

---

## 🚀 Setup Guide

### Prerequisites

- Python 3.10+ installed on your machine.
- A Google account (Gmail) you want to monitor.
- A [Google AI Studio](https://aistudio.google.com/) account to get a Gemini API key.
- A [Google Cloud Console](https://console.cloud.google.com/) account (free tier is enough).

---

### Step 1 — Get `credentials.json` from Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (e.g. `my-email-agent`).
2. In the left menu go to **APIs & Services > Library** and enable:
   - **Gmail API**
   - **Google Calendar API**
3. Go to **APIs & Services > OAuth consent screen**:
   - Choose **External** and click **Create**.
   - Fill in the app name (e.g. `Email Agent`) and your email.
   - Under **Test users**, add your Gmail address.
4. Go to **APIs & Services > Credentials**:
   - Click **Create credentials > OAuth client ID**.
   - Application type: **Desktop app**.
   - Click **Create** and download the JSON file.
5. Save/rename the downloaded file as `credentials.json` in the root of this project:
   ```
   email-agent/credentials.json
   ```

> ⚠️ **Never commit `credentials.json` to Git.** It is already listed in `.gitignore`.

---

### Step 2 — Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Create API key** and copy the generated key.
3. You will use this in Step 3 below.

> ⚠️ **This key is a secret. Never hardcode it in source files or commit it.**

---

### Step 3 — Configure your environment variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
# Required — your Gemini API key from Google AI Studio
GEMINI_API_KEY=your_gemini_api_key_here

# Timezone for the weekly schedule (IANA format)
USER_TIMEZONE=America/New_York

# Day of week and time for the weekly report
REPORT_DAY=friday
REPORT_HOUR=12
REPORT_MINUTE=0

# How many days back to look for emails
DAYS_BACK=7
MAX_EMAIL_CANDIDATES=100

# Optional — recipient email (leave empty to send to your own authenticated account)
REPORT_RECIPIENT_EMAIL=
```

A full list of supported IANA timezone names is available at
[https://en.wikipedia.org/wiki/List_of_tz_database_time_zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

---

### Step 4 — Install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 5 — Authenticate with Google (first time only)

With `credentials.json` and `.env` in place, run:

```bash
python agent.py auth
```

A browser window will open asking you to authorize the agent to:
- Read your Gmail inbox.
- Send emails (the weekly report) on your behalf.
- Create and manage events in your Google Calendar.

After you approve, a `token.json` file is generated automatically and saved locally.

> ⚠️ **Never share or commit `token.json`.** It grants full access to your account.

---

### Step 6 — Run the agent manually (optional test)

To trigger the full pipeline and receive a report in your inbox right now:

```bash
python agent.py run
```

---

### Step 7 — Enable the weekly schedule

#### Option A — GitHub Actions (recommended)

This is the simplest and most reliable option: the agent runs in the cloud with no local machine required.

1. Push this repository to GitHub.
2. Go to your repository **Settings > Secrets and variables > Actions**.
3. Add the following secrets:

   | Secret name | Value |
   |---|---|
   | `GEMINI_API_KEY` | Your Gemini API key from Google AI Studio |
   | `GOOGLE_CREDENTIALS_JSON` | The **full content** (paste as text) of `credentials.json` |
   | `GOOGLE_TOKEN_JSON` | The **full content** (paste as text) of `token.json` |

4. The workflow in `.github/workflows/weekly_report.yml` will fire automatically every Friday.
5. You can also trigger it manually from **Actions > 📊 Reporte Semanal > Run workflow**.

> ⚠️ `GEMINI_API_KEY` must be a **Gemini API key** from AI Studio — not `credentials.json`,
> not `token.json`, and not an OAuth token. The workflow will reject the wrong type with a clear error.

#### Option B — Local cron (alternative)

If you prefer to run on your own machine instead of GitHub Actions:

```bash
# Add a cron job for Fridays at 12:00 PM in your local time
crontab -e
# Add the line below (adjust the path):
0 12 * * 5 /path/to/email-agent/venv/bin/python /path/to/email-agent/agent.py run
```

> Do **not** run both GitHub Actions and a local cron simultaneously — the agent checks Sent Mail
> and skips duplicate reports, but running both is wasteful. Disable one before enabling the other.

---

## 🛠️ Available Commands

| Command | Description |
|:---|:---|
| `python agent.py run` | Run the full pipeline and send the weekly report (skips if one was already sent today) |
| `python agent.py run --force` | Force-send the report even if one was already sent today |
| `python agent.py auth` | Verify or renew Google OAuth authentication |
| `python agent.py list-events` | Show detected deadlines and calendar events awaiting confirmation |
| `python agent.py confirm evt-1` | Add a specific detected event to your Google Calendar |
| `python agent.py confirm all` | Add all pending detected events to your Google Calendar |

---

## 🔐 Security Notes

| File | Contains | Should be committed? |
|:---|:---|:---:|
| `.env` | Gemini API key, timezone, schedule config | ❌ No |
| `credentials.json` | Google OAuth client secret | ❌ No |
| `token.json` | OAuth access & refresh token | ❌ No |
| `.env.example` | Template with placeholder values only | ✅ Yes |
| `requirements.txt` | Python package list (no secrets) | ✅ Yes |

All sensitive files are covered by `.gitignore`. Before sharing or publishing the repository, run:

```bash
git status
```

and confirm that `credentials.json`, `token.json`, and `.env` do **not** appear as tracked files.

---

## 🤖 How it works

```
Gmail Inbox
    │
    ▼
[1] Fetch recent emails (last N days)
    │
    ▼
[2] AI triage — filter out promotions, newsletters, spam
    │
    ▼
[3] AI analysis — extract summary, to-do list, calendar events
    │
    ▼
[4] Generate one-click Google Calendar links for each event
    │
    ▼
[5] Send HTML report to your inbox
```

The AI step uses a **model cascade**: it tries `gemini-3.8-flash` first and falls back through
`gemini-3.7-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, and `gemini-3.1-flash-lite`
automatically if the primary model is unavailable.

---

## 🐛 Troubleshooting

**`credentials.json` not found**
→ Complete Step 1. The file must be in the project root.

**Authentication fails / browser does not open**
→ Make sure your Gmail address is added as a **Test user** in the Google Cloud OAuth consent screen.

**`GEMINI_API_KEY` rejected (401 / 403)**
→ The key must come from [Google AI Studio](https://aistudio.google.com/app/apikey), not from Google Cloud. It starts with `AIza...`, not `ya29...`.

**Report already sent — skipping**
→ The agent found a report in your Sent folder for today. Use `python agent.py run --force` to resend intentionally.

**GitHub Actions: secret is empty**
→ Verify the secret names match exactly: `GEMINI_API_KEY`, `GOOGLE_CREDENTIALS_JSON`, `GOOGLE_TOKEN_JSON`.
