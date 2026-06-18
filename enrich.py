"""Light company enrichment: pull homepage text to feed the LLM a real hook."""
import re

import requests
from bs4 import BeautifulSoup


def fetch_website_text(url, max_chars=2000):
    """Return cleaned visible text from a company homepage, or '' on failure."""
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        resp = requests.get(
            url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (outreach-agent)"}
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
        return text[:max_chars]
    except Exception:
        # Enrichment is best-effort; the one-line blurb is enough on its own.
        return ""
