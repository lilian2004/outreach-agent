# Outreach Agent — AI outreach automation

> An AI agent that runs my own internship search end to end: it drafts a personalized email per founder, sends it from my Gmail, detects replies, and follows up automatically — human-in-the-loop, with a web dashboard.

**Code:** https://github.com/lilian2004/outreach-agent · **Case study:** https://pepper-airboat-8ad.notion.site/Outreach-Agent-AI-outreach-automation-383d71c94d8881d1b15dea626a0ea325

![Dashboard: pipeline, statuses, reply rate and daily to-dos](https://raw.githubusercontent.com/lilian2004/outreach-agent/main/docs/dashboard.png)

---

## The problem

I needed to reach dozens of startup founders, each with a message that actually reflected what their company does. By hand it's slow, inconsistent, and impossible to follow up on reliably — so I built the whole thing into one pipeline: research a founder, draft a tailored email, review, send, detect replies, follow up. A tool to run (and prove) my own internship search, exactly the kind of work a Founder's Associate does.

## What it does

- Imports a list of target founders
- Generates a **personalized email per founder** with an LLM, based on what their company actually does
- Lets me **review before anything is sent** (human-in-the-loop)
- Sends from my own Gmail and **detects replies**
- **Follows up automatically** at J+4 / J+10 — skipping anyone who already replied
- A **web dashboard** tracks the whole pipeline: statuses, stats, reply rate, daily to-dos

## How it works

```
CSV import ──▶ SQLite (founders, emails, statuses)
                  │
                  ├─▶ LLM layer (Groq / Claude) ──▶ draft email
                  │
        review & approve  (human-in-the-loop)
                  │
                  ├─▶ SMTP send (from my Gmail)
                  ├─▶ IMAP poll ──▶ reply detection ──▶ status update
                  └─▶ scheduler ──▶ auto follow-up (J+4 / J+10)

Flask dashboard reads SQLite ──▶ pipeline · stats · reply rate · daily to-dos
```

## Stack

`Python` · `Flask` (dashboard) · `SQLite` · `Groq LLM API` · `SMTP/IMAP` · `BeautifulSoup` · `pytest`

## Key decisions

- **Semi-automated, not a spam bot** — the AI drafts, I approve. Dry-run mode + daily send cap protect deliverability.
- **No LinkedIn scraping** — respects platform terms of service; email channel only.
- **Secrets out of code** — API keys and credentials live in a gitignored `.env`, never committed.
- **Provider-agnostic LLM layer** — switch between free Groq and Claude by changing one variable.
- **Tested** — the data layer is covered by unit tests on a temporary database (`pytest`).

## Result

Running live on my own search: 19 founders contacted so far, 2 replied within 24h (one positive), follow-ups still in flight. Built, tested and shipped solo — it generates, sends, tracks and auto-follows-up on real campaigns end to end. The project itself is the demonstration: take a manual, repetitive process and turn it into a system.

## Getting started

> Adjust file/entrypoint names to match the repo.

```bash
git clone https://github.com/lilian2004/outreach-agent.git
cd outreach-agent

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # fill in your keys (never committed)
python app.py
```

| Variable | Description |
|---|---|
| `GMAIL_ADDRESS` | Sender Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail app password (not your account password) |
| `GROQ_API_KEY` / `ANTHROPIC_API_KEY` | LLM API key |
| `LLM_PROVIDER` | `groq` or `claude` |
| `DAILY_SEND_CAP` | Max emails per day (deliverability guard) |

## What's next

A/B testing on subject lines with open-rate tracking, LLM-based reply classification (positive / negative / later), and per-segment templates with conversion analytics.

---

### About

Built by **Lilian Miceli** — I take work off a founder's plate and ship it to production, solo.
[LinkedIn](https://www.linkedin.com/in/lilian-miceli-451ab0235/) · lilianmiceli38@gmail.com
