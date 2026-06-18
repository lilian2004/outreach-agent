"""Generate a personalized outreach email with an LLM.

Supports two providers, selected by LLM_PROVIDER in .env:
  - "groq"      -> free, no credit card (uses the OpenAI-compatible Groq API)
  - "anthropic" -> paid (Claude)
"""
import json
import re

import config

PROMPT_TEMPLATE = """You are helping Lilian, a Master's student in Information Systems Management, write a SHORT, sharp cold email to the founder of an early-stage startup. Lilian wants a 6-month internship as the founder's right hand (operations / product / growth), starting September, in Barcelona or remote.

Lilian's proof (use only what's relevant, never list it all): he rebuilt a company's entire system solo (website -> Supabase -> Retool admin dashboards, automations, metrics tracking), shipped it to production, then ran it in autonomy alongside the CEO. Finance background, so he thinks in conversion, churn, CAC/LTV and unit economics.

WRITE THE EMAIL LIKE THIS:
1. FIRST SENTENCE = a sharp, specific observation about THIS company's actual mechanic, framed as a real business challenge. Name the concrete thing they do. Show you understand WHY it's hard, not just what sector they're in.
2. Then connect Lilian's proof to that challenge in one or two sentences (autonomy + the build + the finance lens).
3. Then the ask: a 6-month internship from September, executing concrete work inside a small team.
4. Then a light CTA: a 15-minute call this week.

HARD RULES:
- NEVER open with "I noticed", "I came across", "I'm reaching out", "I'm writing to", "I am interested in", or "I'd love to". Open straight into the observation.
- Tone: confident, peer-to-peer, concrete. No flattery, no "I'd love to learn", no buzzwords, no emojis.
- Specific over generic: if you can't say something true and precise about their model, say nothing.
- 90-140 words in the body. Do NOT use the phrase "Founder's Associate".
- End the body with the portfolio link on its own final line: {portfolio_url}
- Output STRICT JSON only, nothing else: {{"subject": "...", "body": "..."}}

GOOD EXAMPLE (for a fictional B2B payments startup, copy the STYLE not the words):
{{"subject": "6-month internship — September start", "body": "Turning failed payments into recovered revenue lives or dies on retry logic and timing — a margin problem disguised as an engineering one. I recently built and ran a company's whole system solo (site, Supabase, Retool dashboards, automations) and shipped it to production next to the CEO, so I'm comfortable owning execution and reading the numbers underneath it. My finance background means I think in recovery rate and unit economics. I'm after a 6-month internship from September to take real work off your plate. Open to a quick 15-minute call this week?\\nhttps://example.com"}}

NOW WRITE FOR:
COMPANY: {company}
WHAT THEY DO: {blurb}
WEBSITE EXCERPT: {website_text}
CONTACT: {contact_name} ({title})
"""


def _call_groq(prompt):
    from openai import OpenAI  # Groq exposes an OpenAI-compatible API

    client = OpenAI(
        api_key=config.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _call_anthropic(prompt):
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def generate_email(prospect, website_text=""):
    """Return (subject, body) for a prospect dict."""
    prompt = PROMPT_TEMPLATE.format(
        portfolio_url=config.PORTFOLIO_URL,
        company=prospect.get("company", ""),
        blurb=prospect.get("company_blurb", "") or "(no description provided)",
        website_text=website_text or "(none)",
        contact_name=prospect.get("contact_name") or "there",
        title=prospect.get("title", ""),
    )

    if config.LLM_PROVIDER == "anthropic":
        text = _call_anthropic(prompt)
    else:
        text = _call_groq(prompt)

    text = text.strip()
    # Strip code fences if the model wrapped the JSON.
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # Keep only the JSON object, in case the model added stray text around it.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)
    # strict=False tolerates literal newlines inside the JSON string values.
    data = json.loads(text, strict=False)
    return data["subject"], data["body"]
