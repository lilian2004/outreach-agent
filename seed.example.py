"""Example seed data (anonymised). Safe to keep in a public repo.

To load your own real prospects locally:
  cp seed.example.py seed.py     # seed.py is gitignored, stays private
  # edit seed.py with your real data, then:
  python seed.py
"""
import db

# company, contact, title, email, linkedin, website, blurb, status, sent_at, replied, notes
PROSPECTS = [
    ("Acme SaaS", "Jane Doe", "CEO & Founder", "jane@acme.example",
     "linkedin.com/in/example", "acme.example",
     "B2B SaaS — example company", "replied", "2026-01-10", 1,
     "Example: positive reply, call scheduled."),
    ("Beta Labs", "John Smith", "Co-Founder", "john@beta.example",
     "linkedin.com/in/example", "beta.example",
     "Early-stage AI startup — example company", "sent", "2026-01-11", 0,
     "Example: email + LinkedIn sent."),
    ("Gamma Studio", "Alex Roe", "Founder", "",
     "linkedin.com/in/example", "gamma.example",
     "D2C brand — example company", "refused", "2026-01-11", 1,
     "Example: polite no, asked for a referral."),
]


def seed():
    db.init_db()
    with db.get_conn() as conn:
        conn.execute("DELETE FROM prospects")
    for (company, contact, title, email, linkedin, website, blurb,
         status, sent_at, replied, notes) in PROSPECTS:
        db.add_prospect(
            company=company, contact_name=contact, title=title, email=email,
            linkedin=linkedin, website=website, company_blurb=blurb,
            status=status, sent_at=sent_at, replied=replied, notes=notes,
        )
    print(f"{len(PROSPECTS)} example prospects loaded.")


if __name__ == "__main__":
    seed()
