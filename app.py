"""Local web dashboard for the outreach agent.

Run it with:  python app.py
Then open:     http://localhost:5000

Everything runs on your machine — your keys never leave it.
"""
from datetime import date

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    flash,
)

import config
import db
import enrich
import generate
import emailer

app = Flask(__name__)
app.secret_key = "local-dashboard"  # only used for flash messages, local-only

db.init_db()

STATUS_LABEL = {
    "new": ("Nouveau", "#888780"),
    "drafted": ("Brouillon", "#BA7517"),
    "sent": ("Envoyé", "#185FA5"),
    "followup1": ("Relancé J+4", "#534AB7"),
    "followup2": ("Relancé J+10", "#534AB7"),
    "replied": ("Répondu", "#0F6E56"),
    "refused": ("Refus", "#A32D2D"),
    "closed": ("Clos", "#888780"),
}

CONTACTED = {"sent", "followup1", "followup2", "replied", "refused"}

STYLE = """
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 980px; margin: 0 auto; padding: 24px; color: #1a1a1a; background: #fafaf8; }
  a { color: #185FA5; text-decoration: none; }
  h1 { font-size: 22px; font-weight: 600; margin: 0 0 4px; }
  h2 { font-size: 17px; font-weight: 600; margin: 24px 0 12px; }
  .sub { color: #6b6b66; font-size: 14px; margin: 0 0 20px; }
  .nav { display: flex; gap: 16px; margin: 0 0 20px; font-size: 14px; }
  .nav a.active { font-weight: 600; color: #1a1a1a; }
  .stats { display: flex; gap: 12px; margin: 0 0 24px; flex-wrap: wrap; }
  .stat { background: #fff; border: 1px solid #e7e6e0; border-radius: 10px; padding: 12px 18px; min-width: 110px; }
  .stat .n { font-size: 24px; font-weight: 600; }
  .stat .l { font-size: 12px; color: #6b6b66; }
  table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e7e6e0; border-radius: 10px; overflow: hidden; }
  th, td { text-align: left; padding: 11px 14px; font-size: 14px; border-bottom: 1px solid #f0efe9; }
  th { background: #f5f4ef; font-weight: 500; color: #6b6b66; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 20px; color: #fff; }
  .btn { display: inline-block; font-size: 13px; padding: 7px 13px; border-radius: 8px; border: 1px solid #d8d7d0;
         background: #fff; color: #1a1a1a; cursor: pointer; }
  .btn:hover { background: #f5f4ef; }
  .btn-primary { background: #185FA5; color: #fff; border-color: #185FA5; }
  .btn-primary:hover { background: #144f8a; }
  .card { background: #fff; border: 1px solid #e7e6e0; border-radius: 10px; padding: 20px; margin: 0 0 16px; }
  .flash { background: #E1F5EE; color: #0F6E56; border: 1px solid #9FE1CB; border-radius: 8px; padding: 10px 14px; margin: 0 0 16px; font-size: 14px; }
  input[type=text], input[type=email], textarea, input[type=file] { width: 100%; padding: 9px 11px; border: 1px solid #d8d7d0; border-radius: 8px; font-size: 14px; font-family: inherit; }
  textarea { min-height: 180px; line-height: 1.6; }
  label { font-size: 13px; color: #6b6b66; display: block; margin: 12px 0 5px; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .toolbar { display: flex; gap: 10px; margin: 0 0 20px; flex-wrap: wrap; align-items: center; }
  .muted { color: #6b6b66; font-size: 13px; }
  details summary { cursor: pointer; font-size: 14px; font-weight: 500; color: #185FA5; }
  .bar-track { background: #f0efe9; border-radius: 6px; height: 26px; overflow: hidden; }
  .bar-fill { height: 100%; }
</style>
"""

NAV = """
<div class="nav">
  <a href="/" class="{{ 'active' if page=='home' else '' }}">Tableau de bord</a>
  <a href="/stats" class="{{ 'active' if page=='stats' else '' }}">Statistiques</a>
</div>
"""


GOAL = 50  # ton objectif de boîtes contactées — change ce chiffre si tu veux


def badge(status):
    label, color = STATUS_LABEL.get(status, (status, "#888780"))
    return f'<span class="badge" style="background:{color}">{label}</span>'


INDEX_HTML = STYLE + NAV + """
<h1>Outreach Agent</h1>
<p class="sub">Ton tableau de bord de prospection — {{ total }} prospects.</p>

{% with messages = get_flashed_messages() %}
  {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
{% endwith %}

<div class="stats">
  <div class="stat"><div class="n">{{ total }}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n">{{ contacted }}</div><div class="l">Contactés</div></div>
  <div class="stat"><div class="n">{{ counts.get('replied',0) }}</div><div class="l">Réponses +</div></div>
  <div class="stat"><div class="n">{{ counts.get('new',0) + counts.get('drafted',0) }}</div><div class="l">À traiter</div></div>
</div>

<div class="card">
  <h2 style="margin-top:0">Aujourd'hui</h2>
  <div class="row" style="gap:28px">
    <div><div style="font-size:22px;font-weight:600">{{ due|length }}</div><div class="muted">relance(s) à envoyer</div></div>
    <div><div style="font-size:22px;font-weight:600">{{ to_send }}</div><div class="muted">brouillon(s) à envoyer</div></div>
    <div><div style="font-size:22px;font-weight:600">{{ to_draft }}</div><div class="muted">à drafter</div></div>
  </div>
  {% if due %}
  <p class="muted" style="margin-top:14px">Relances dues : {% for p in due %}<a href="/prospect/{{ p.id }}">{{ p.company }}</a>{% if not loop.last %}, {% endif %}{% endfor %}</p>
  {% else %}
  <p class="muted" style="margin-top:14px">Aucune relance due aujourd'hui.</p>
  {% endif %}
  <div style="margin-top:16px">
    <div class="row" style="justify-content:space-between"><span class="muted">Objectif : {{ contacted }}/{{ goal }} contactés</span><span class="muted">{{ goal_pct }}%</span></div>
    <div class="bar-track"><div class="bar-fill" style="width:{{ goal_pct }}%; background:#0F6E56"></div></div>
  </div>
</div>

<div class="toolbar">
  <form method="post" action="/import" enctype="multipart/form-data" class="row">
    <input type="file" name="csv" accept=".csv" style="width:auto" />
    <button class="btn" type="submit">Importer CSV</button>
  </form>
  <form method="post" action="/followup" class="row">
    <input type="hidden" name="stage" value="1" />
    <button class="btn" type="submit" onclick="return confirm('Envoyer les relances J+4 dues maintenant ?')">Lancer les relances J+4</button>
  </form>
</div>

<details class="card">
  <summary>+ Ajouter un prospect</summary>
  <form method="post" action="/add" style="margin-top:14px">
    <div class="grid2">
      <div><label>Entreprise *</label><input type="text" name="company" required></div>
      <div><label>Contact (founder)</label><input type="text" name="contact_name"></div>
      <div><label>Titre</label><input type="text" name="title" placeholder="CEO, Founder…"></div>
      <div><label>Email</label><input type="email" name="email"></div>
      <div><label>Site web</label><input type="text" name="website" placeholder="exemple.com"></div>
      <div><label>LinkedIn</label><input type="text" name="linkedin"></div>
    </div>
    <label>Ce qu'ils font (1 ligne, pour l'IA)</label>
    <input type="text" name="company_blurb">
    <div style="margin-top:14px"><button class="btn btn-primary" type="submit">Ajouter</button></div>
  </form>
</details>

<table>
  <tr><th>#</th><th>Entreprise</th><th>Contact</th><th>Email</th><th>Statut</th><th></th></tr>
  {% for p in prospects %}
  <tr>
    <td>{{ p.id }}</td>
    <td>{{ p.company }}</td>
    <td>{{ p.contact_name or '' }}</td>
    <td class="muted">{{ p.email or '—' }}</td>
    <td>{{ badge(p.status)|safe }}</td>
    <td><a href="/prospect/{{ p.id }}">Ouvrir →</a></td>
  </tr>
  {% endfor %}
  {% if not prospects %}
  <tr><td colspan="6" class="muted" style="padding:24px;text-align:center">Aucun prospect. Importe un CSV ou ajoute-en un.</td></tr>
  {% endif %}
</table>
"""


DETAIL_HTML = STYLE + NAV + """
<p><a href="/">← Retour au tableau de bord</a></p>
<h1>{{ p.company }}</h1>
<p class="sub">{{ p.contact_name or '' }}{% if p.title %} · {{ p.title }}{% endif %} · {{ badge(p.status)|safe }}</p>

{% with messages = get_flashed_messages() %}
  {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
{% endwith %}

<div class="card">
  <div class="row" style="justify-content:space-between">
    <span class="muted">Email : {{ p.email or '— aucun —' }}{% if p.website %} · {{ p.website }}{% endif %}</span>
    <form method="post" action="/draft/{{ p.id }}">
      <button class="btn btn-primary" type="submit">{% if p.draft_body %}Régénérer le brouillon (IA){% else %}Générer le brouillon (IA){% endif %}</button>
    </form>
  </div>
</div>

{% if p.draft_body %}
<form method="post" action="/prospect/{{ p.id }}/save" class="card">
  <label>Objet</label>
  <input type="text" name="subject" value="{{ p.draft_subject or '' }}" />
  <label>Corps</label>
  <textarea name="body">{{ p.draft_body }}</textarea>
  <div class="row" style="margin-top:14px">
    <button class="btn" type="submit">Enregistrer les modifications</button>
  </div>
</form>

<div class="card">
  <div class="row">
    <form method="post" action="/send/{{ p.id }}">
      <input type="hidden" name="dry" value="1" />
      <button class="btn" type="submit">Aperçu (sans envoyer)</button>
    </form>
    <form method="post" action="/send/{{ p.id }}">
      <input type="hidden" name="dry" value="0" />
      <button class="btn btn-primary" type="submit" onclick="return confirm('Envoyer cet email pour de vrai à {{ p.email }} ?')">Envoyer l'email</button>
    </form>
  </div>
</div>
{% else %}
<p class="muted">Génère un brouillon pour voir l'email personnalisé, le relire, puis l'envoyer.</p>
{% endif %}

<div class="card">
  <label style="margin-top:0">Changer le statut</label>
  <div class="row">
    <form method="post" action="/prospect/{{ p.id }}/status"><input type="hidden" name="status" value="replied"><button class="btn" type="submit">Répondu +</button></form>
    <form method="post" action="/prospect/{{ p.id }}/status"><input type="hidden" name="status" value="refused"><button class="btn" type="submit">Refus</button></form>
    <form method="post" action="/prospect/{{ p.id }}/status"><input type="hidden" name="status" value="closed"><button class="btn" type="submit">Clos</button></form>
    <form method="post" action="/prospect/{{ p.id }}/status"><input type="hidden" name="status" value="sent"><button class="btn" type="submit">Remettre « Envoyé »</button></form>
  </div>
</div>

<form method="post" action="/prospect/{{ p.id }}/notes" class="card">
  <label style="margin-top:0">Notes</label>
  <textarea name="notes" style="min-height:120px">{{ p.notes or '' }}</textarea>
  <div style="margin-top:12px"><button class="btn" type="submit">Enregistrer les notes</button></div>
</form>
"""


STATS_HTML = STYLE + NAV + """
<h1>Statistiques</h1>
<p class="sub">Mesure ta prospection comme un growth.</p>

<div class="stats">
  <div class="stat"><div class="n">{{ contacted }}</div><div class="l">Contactés</div></div>
  <div class="stat"><div class="n">{{ responses }}</div><div class="l">Réponses</div></div>
  <div class="stat"><div class="n">{{ reply_rate }}%</div><div class="l">Taux de réponse</div></div>
  <div class="stat"><div class="n">{{ counts.get('replied',0) }}</div><div class="l">Réponses positives</div></div>
</div>

<div class="card">
  <h2 style="margin-top:0">Funnel</h2>
  {% for label, n, color in funnel %}
  <div style="margin-bottom:12px">
    <div class="row" style="justify-content:space-between"><span class="muted">{{ label }}</span><span class="muted">{{ n }}</span></div>
    <div class="bar-track"><div class="bar-fill" style="width:{{ (n / maxbar * 100) if maxbar else 0 }}%; background:{{ color }}"></div></div>
  </div>
  {% endfor %}
</div>

<p class="muted">Taux de réponse = réponses (positives + refus) ÷ contactés. Vise 10-20% — au-dessus, ton ciblage et tes accroches sont bons.</p>
"""


@app.route("/")
def index():
    prospects = db.list_prospects()
    counts = {}
    for p in prospects:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    contacted = sum(counts.get(s, 0) for s in CONTACTED)
    due = db.due_for_followup(1) + db.due_for_followup(2)
    goal_pct = min(round(contacted / GOAL * 100), 100) if GOAL else 0
    return render_template_string(
        INDEX_HTML, prospects=prospects, total=len(prospects),
        counts=counts, contacted=contacted, badge=badge, page="home",
        due=due, to_draft=counts.get("new", 0), to_send=counts.get("drafted", 0),
        goal=GOAL, goal_pct=goal_pct,
    )


@app.route("/add", methods=["POST"])
def do_add():
    company = (request.form.get("company") or "").strip()
    if not company:
        flash("Le nom de l'entreprise est requis.")
        return redirect(url_for("index"))
    fields = {"company": company, "status": "new"}
    for k in ("contact_name", "title", "email", "website", "linkedin", "company_blurb"):
        v = (request.form.get(k) or "").strip()
        if v:
            fields[k] = v
    db.add_prospect(**fields)
    flash(f"{company} ajouté.")
    return redirect(url_for("index"))


@app.route("/import", methods=["POST"])
def do_import():
    f = request.files.get("csv")
    if f and f.filename:
        path = "/tmp/_oa_upload.csv"
        f.save(path)
        n = db.import_csv(path)
        flash(f"{n} prospects importés.")
    else:
        flash("Aucun fichier sélectionné.")
    return redirect(url_for("index"))


@app.route("/prospect/<int:pid>")
def prospect(pid):
    p = db.get_prospect(pid)
    if not p:
        return redirect(url_for("index"))
    return render_template_string(DETAIL_HTML, p=p, badge=badge, page="home")


@app.route("/draft/<int:pid>", methods=["POST"])
def do_draft(pid):
    p = db.get_prospect(pid)
    if p:
        text = enrich.fetch_website_text(p.get("website")) if p.get("website") else ""
        try:
            subject, body = generate.generate_email(p, text)
            db.update_prospect(pid, draft_subject=subject, draft_body=body, status="drafted")
            flash("Brouillon généré par l'IA.")
        except Exception as e:
            flash(f"Erreur de génération : {e}")
    return redirect(url_for("prospect", pid=pid))


@app.route("/prospect/<int:pid>/save", methods=["POST"])
def save_draft(pid):
    db.update_prospect(
        pid,
        draft_subject=request.form.get("subject", ""),
        draft_body=request.form.get("body", ""),
    )
    flash("Brouillon enregistré.")
    return redirect(url_for("prospect", pid=pid))


@app.route("/prospect/<int:pid>/notes", methods=["POST"])
def save_notes(pid):
    db.update_prospect(pid, notes=request.form.get("notes", ""))
    flash("Notes enregistrées.")
    return redirect(url_for("prospect", pid=pid))


@app.route("/prospect/<int:pid>/status", methods=["POST"])
def set_status(pid):
    status = request.form.get("status", "sent")
    replied = 1 if status in ("replied", "refused", "closed") else 0
    db.update_prospect(pid, status=status, replied=replied)
    flash(f"Statut mis à jour : {STATUS_LABEL.get(status, (status,))[0]}.")
    return redirect(url_for("prospect", pid=pid))


@app.route("/send/<int:pid>", methods=["POST"])
def do_send(pid):
    p = db.get_prospect(pid)
    dry = request.form.get("dry") == "1"
    if not p or not p.get("draft_body"):
        flash("Génère d'abord un brouillon.")
        return redirect(url_for("prospect", pid=pid))
    if not p.get("email"):
        flash("Pas d'email pour ce prospect.")
        return redirect(url_for("prospect", pid=pid))
    try:
        emailer.send_email(p["email"], p["draft_subject"], p["draft_body"], dry_run=dry)
        if dry:
            flash("Aperçu affiché dans le terminal — rien n'a été envoyé.")
        else:
            db.update_prospect(pid, status="sent", sent_at=date.today().isoformat())
            flash(f"Email envoyé à {p['email']}.")
    except Exception as e:
        flash(f"Erreur d'envoi : {e}")
    return redirect(url_for("prospect", pid=pid))


@app.route("/followup", methods=["POST"])
def do_followup():
    stage = int(request.form.get("stage", 1))
    due = db.due_for_followup(stage)
    sent = 0
    skipped = 0
    for p in due:
        since = p.get("sent_at") or date.today().isoformat()
        if emailer.has_reply_from(p.get("email"), since):
            db.update_prospect(p["id"], replied=1, status="replied")
            skipped += 1
            continue
        first = (p.get("contact_name") or "").split(" ")[0]
        body = (
            f"Hi {first},\n\nJust bringing this back to the top of your inbox in case it "
            "slipped through — still very interested and available for a quick 15-minute "
            f"call this week.\n\nBest,\n{config.SENDER_NAME}\n{config.PORTFOLIO_URL}"
        )
        subject = "Re: " + (p.get("draft_subject") or "Quick follow-up")
        try:
            emailer.send_email(p["email"], subject, body, dry_run=False)
            field = "followup1_at" if stage == 1 else "followup2_at"
            new_status = "followup1" if stage == 1 else "followup2"
            db.update_prospect(p["id"], status=new_status, **{field: date.today().isoformat()})
            sent += 1
        except Exception:
            pass
    flash(f"Relances : {sent} envoyée(s), {skipped} sautée(s) (déjà répondu).")
    return redirect(url_for("index"))


@app.route("/stats")
def stats():
    prospects = db.list_prospects()
    counts = {}
    for p in prospects:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    contacted = sum(counts.get(s, 0) for s in CONTACTED)
    responses = counts.get("replied", 0) + counts.get("refused", 0)
    reply_rate = round(responses / contacted * 100) if contacted else 0
    funnel = [
        ("À traiter", counts.get("new", 0) + counts.get("drafted", 0), "#888780"),
        ("Envoyés", counts.get("sent", 0) + counts.get("followup1", 0) + counts.get("followup2", 0), "#185FA5"),
        ("Réponses positives", counts.get("replied", 0), "#0F6E56"),
        ("Refus", counts.get("refused", 0), "#A32D2D"),
    ]
    maxbar = max((n for _, n, _ in funnel), default=0)
    return render_template_string(
        STATS_HTML, counts=counts, contacted=contacted, responses=responses,
        reply_rate=reply_rate, funnel=funnel, maxbar=maxbar, page="stats",
    )


if __name__ == "__main__":
    print("Dashboard : http://localhost:5000")
    app.run(port=5000, debug=False)
