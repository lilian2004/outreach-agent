"""Central configuration, loaded from environment variables (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM ---
# Provider can be "groq" (free, no credit card) or "anthropic" (paid).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Model defaults to a sensible choice per provider; override with LLM_MODEL.
_DEFAULT_MODEL = {
    "groq": "llama-3.3-70b-versatile",
    "anthropic": "claude-sonnet-4-5",
}
LLM_MODEL = os.getenv("LLM_MODEL", _DEFAULT_MODEL.get(LLM_PROVIDER, "llama-3.3-70b-versatile"))

# --- Email (SMTP to send, IMAP to detect replies) ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").replace(" ", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Lilian Miceli")

# --- Personal assets injected into every email ---
PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "")

# --- Sending safety ---
DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "15"))
FOLLOWUP_1_DAYS = int(os.getenv("FOLLOWUP_1_DAYS", "4"))
FOLLOWUP_2_DAYS = int(os.getenv("FOLLOWUP_2_DAYS", "10"))

DB_PATH = os.getenv("DB_PATH", "outreach.db")
