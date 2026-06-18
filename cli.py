"""Command-line interface for the founder outreach agent.

Commands:
  init                       create the database
  import <csv>               import an Apollo CSV export
  list [--status STATUS]     show the pipeline
  draft --id N               generate a personalized email for prospect N
  send  --id N [--dry-run]   send the drafted email (preview with --dry-run)
  followup --stage {1,2} [--dry-run]
                             send follow-ups that are due, skipping replies
"""
import argparse
from datetime import date

import config
import db
import enrich
import generate
import emailer


def cmd_init(args):
    db.init_db()
    print(f"DB ready at {config.DB_PATH}")


def cmd_import(args):
    db.init_db()
    n = db.import_csv(args.csv)
    print(f"Imported {n} prospects.")


def cmd_list(args):
    rows = db.list_prospects(args.status)
    if not rows:
        print("No prospects.")
        return
    for p in rows:
        print(
            f"[{p['id']:>3}] {p['status']:<9} "
            f"{p['company']:<24} {(p.get('contact_name') or ''):<20} "
            f"{p.get('email') or ''}"
        )


def cmd_draft(args):
    p = db.get_prospect(args.id)
    if not p:
        print("No such prospect.")
        return
    website_text = enrich.fetch_website_text(p.get("website")) if p.get("website") else ""
    subject, body = generate.generate_email(p, website_text)
    db.update_prospect(args.id, draft_subject=subject, draft_body=body, status="drafted")
    print(f"\nSubject: {subject}\n\n{body}\n")
    print(f"Review it, then: python cli.py send --id {args.id} --dry-run")


def cmd_send(args):
    p = db.get_prospect(args.id)
    if not p or not p.get("draft_body"):
        print("Draft this prospect first (draft --id N).")
        return
    if not p.get("email"):
        print("No email on file for this prospect.")
        return
    ok = emailer.send_email(
        p["email"], p["draft_subject"], p["draft_body"], dry_run=args.dry_run
    )
    if ok and not args.dry_run:
        db.update_prospect(args.id, status="sent", sent_at=date.today().isoformat())
        print("Sent + logged.")


def cmd_followup(args):
    due = db.due_for_followup(args.stage)
    print(f"{len(due)} prospect(s) due for follow-up {args.stage}.")
    for p in due:
        # Don't follow up with someone who already answered.
        since = p.get("sent_at") or date.today().isoformat()
        if emailer.has_reply_from(p.get("email"), since):
            db.update_prospect(p["id"], replied=1, status="replied")
            print(f"  [{p['id']}] {p['company']}: reply detected — skipped.")
            continue
        first_name = (p.get("contact_name") or "").split(" ")[0]
        body = (
            f"Hi {first_name},\n\n"
            "Just bringing this back to the top of your inbox in case it slipped "
            "through — still very interested and available for a quick 15-minute "
            "call this week.\n\n"
            f"Best,\n{config.SENDER_NAME}\n{config.PORTFOLIO_URL}"
        )
        subject = "Re: " + (p.get("draft_subject") or "Quick follow-up")
        emailer.send_email(p["email"], subject, body, dry_run=args.dry_run)
        if not args.dry_run:
            if args.stage == 1:
                db.update_prospect(p["id"], status="followup1", followup1_at=date.today().isoformat())
            else:
                db.update_prospect(p["id"], status="followup2", followup2_at=date.today().isoformat())


def build_parser():
    parser = argparse.ArgumentParser(description="Founder outreach automation agent")
    sub = parser.add_subparsers()

    sub.add_parser("init").set_defaults(func=cmd_init)

    p_imp = sub.add_parser("import")
    p_imp.add_argument("csv")
    p_imp.set_defaults(func=cmd_import)

    p_list = sub.add_parser("list")
    p_list.add_argument("--status")
    p_list.set_defaults(func=cmd_list)

    p_draft = sub.add_parser("draft")
    p_draft.add_argument("--id", type=int, required=True)
    p_draft.set_defaults(func=cmd_draft)

    p_send = sub.add_parser("send")
    p_send.add_argument("--id", type=int, required=True)
    p_send.add_argument("--dry-run", action="store_true")
    p_send.set_defaults(func=cmd_send)

    p_fu = sub.add_parser("followup")
    p_fu.add_argument("--stage", type=int, choices=[1, 2], required=True)
    p_fu.add_argument("--dry-run", action="store_true")
    p_fu.set_defaults(func=cmd_followup)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
