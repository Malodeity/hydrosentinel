"""Puts the database in the exact state used for the final presentation: realistic citizen reports across several authorities,
some untouched, some in review, some with a contractor ticket at different stages (one rejected then reassigned), some resolved.

    cd backend && python -m scripts.seed_demo_reports            # dry run, prints what it would do
    cd backend && python -m scripts.seed_demo_reports --apply    # DELETES every existing report, ticket and notification, then seeds

Authorities, contractors and logins are not touched (start the app with SEED_DEMO_DATA=true to create the demo contractors).
Reports are spread over the last 3 weeks so the dashboard trends look real. Run it from docs/a5/reset_demo.sh, which takes a backup first."""
import sys
import uuid
from datetime import datetime, timedelta, timezone

from app import assignment_helpers as helpers
from app import models
from app.database import SessionLocal

# (authority name, issue, description, days ago, state)   state: open | review | assigned | accepted | working | fixed | rejected_then_working | resolved
REPORTS = [
    ("City of Ekurhuleni", "leak", "Water main leaking at the corner of Atlas Road and Rosewood Street, flowing into the road since Monday.", 2, "open"),
    ("City of Ekurhuleni", "outage", "No water in Tembisa Extension 5 since yesterday morning. Tanker has not arrived.", 1, "assigned"),
    ("City of Ekurhuleni", "quality", "Tap water is brown and smells of soil in Kempton Park, residents are boiling water.", 4, "accepted"),
    ("City of Ekurhuleni", "leak", "Burst pipe outside the clinic in Katlehong, water pooling on the pavement.", 6, "fixed"),
    ("City of Ekurhuleni", "billing", "Account shows R14 000 for a stand with a single tap. Third month in a row.", 9, "review"),
    ("City of Ekurhuleni", "leak", "Leaking meter box on Pretoria Road repaired last week, no more water on the street.", 14, "resolved"),
    ("City of Johannesburg", "outage", "Soweto Orlando East has had no pressure since Friday night, taps only drip.", 3, "open"),
    ("City of Johannesburg", "leak", "Fire hydrant leaking in Jeppestown, a stream runs down the street all day.", 5, "working"),
    ("City of Johannesburg", "quality", "Discoloured water in Alexandra after the maintenance shutdown.", 8, "review"),
    ("City of Johannesburg", "leak", "Manhole overflowing with clean water in Rosebank, report lodged twice before.", 12, "resolved"),
    ("City of Tshwane", "leak", "Large leak on Church Street near the taxi rank, road surface is breaking up.", 2, "assigned"),
    ("City of Tshwane", "outage", "Mamelodi East without water for two days, schools affected.", 4, "rejected_then_working"),
    ("City of Tshwane", "billing", "Estimated readings for six months, no meter reader has visited.", 10, "open"),
    ("City of Cape Town MM", "leak", "Pipe burst on Main Road Observatory, water running into the storm drain.", 1, "open"),
    ("City of Cape Town MM", "quality", "Chlorine smell very strong in Khayelitsha Site C, children complaining.", 7, "review"),
    ("City of Cape Town MM", "leak", "Dripping connection at the Bellville taxi rank fixed and checked.", 16, "resolved"),
    ("eThekwini MM", "outage", "Umlazi V section dry for three days, only a tanker twice a day.", 3, "assigned"),
    ("eThekwini MM", "leak", "Leak at the Chatsworth reservoir overflow, water running for a week.", 7, "open"),
    ("Buffalo City LM", "quality", "Water from the tap is cloudy in Mdantsane NU 2, no notice was given.", 5, "open"),
    ("Mangaung", "leak", "Burst pipe on Nelson Mandela Drive in Bloemfontein, shop owners lost water.", 6, "working"),
    ("Polokwane LM", "outage", "Seshego Zone 4 has had no supply since the pump station failure.", 2, "open"),
    ("City Of Mbombela", "leak", "Continuous leak behind the Riverside mall, dirty water on the road.", 9, "review"),
    ("Msunduzi LM", "quality", "Smell of sewage in tap water in Edendale, three households sick.", 11, "open"),
    ("Sol Plaatje Local Municipality", "outage", "Kimberley Galeshewe low pressure for a week, upper floors have nothing.", 13, "resolved"),
]
LAT_LNG_FALLBACK = (-26.2, 28.0)
ISSUE = {"leak": models.IssueType.leak, "outage": models.IssueType.outage, "quality": models.IssueType.quality, "billing": models.IssueType.billing}


# older, already verified repairs spread over the last 3 months, so a contractor's dashboard has a week, a month and 3 months of history to show.
# a few are fixed after their due time on purpose, so "fixed on time" is not 100%
HISTORY_AGES = [2, 4, 6, 9, 12, 17, 23, 31, 40, 52, 65, 80]


def add_history(db, admin, now) -> int:
    contractors = [c for c in db.query(models.Contractor).filter(models.Contractor.is_active).order_by(models.Contractor.name) if c.coverage][:6]
    count = 0
    for ci, contractor in enumerate(contractors):
        row = contractor.coverage[0]
        issue = helpers.coverage_issue_types(row) and sorted(helpers.coverage_issue_types(row))[0]
        wsa = db.query(models.WSA).filter(models.WSA.id == row.wsa_id).first()
        if not issue or wsa is None:
            continue
        for k in range(5 + ci % 3):
            age = HISTORY_AGES[(ci * 2 + k * 2) % len(HISTORY_AGES)] + k % 2
            given = now - timedelta(days=age, hours=ci)
            due = given + timedelta(hours=helpers.DEFAULT_DUE_HOURS[issue])
            fixed = given + timedelta(hours=5 + (k * 7 + ci * 3) % 30 + (30 if (k + ci) % 4 == 3 else 0))   # every fourth one runs past its due time
            report = models.CitizenReport(
                wsa_id=wsa.id, issue_type=ISSUE[issue], description=f"Earlier {issue} report, repaired and checked.", reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                case_status="resolved", lat=wsa.lat or LAT_LNG_FALLBACK[0], lng=wsa.lng or LAT_LNG_FALLBACK[1], created_at=given - timedelta(hours=2),
                reviewed_by=admin.id if admin else None, reviewed_at=given, resolved_by=admin.id if admin else None, resolved_at=fixed + timedelta(hours=8),
                admin_comment="Repair checked on site and confirmed.",
            )
            db.add(report)
            db.flush()
            db.add(models.ReportAssignment(
                report_id=report.id, contractor_id=contractor.id, assigned_by=admin.id if admin else None, status="closed",
                instructions="Isolate the section, repair, and photograph the finished work.", created_at=given, due_at=due, accepted_at=given + timedelta(minutes=30),
                started_at=given + timedelta(hours=1), fixed_at=fixed, closed_at=fixed + timedelta(hours=8), contractor_note="Repaired and tested the pressure.",
            ))
            count += 1
    return count


def main(apply: bool) -> None:
    db = SessionLocal()
    try:
        print(f"existing: {db.query(models.CitizenReport).count()} reports, {db.query(models.ReportAssignment).count()} tickets, "
              f"{db.query(models.Notification).count()} notifications")
        if not apply:
            print(f"dry run. --apply would replace them with {len(REPORTS)} curated reports.")
            return
        admin = db.query(models.User).filter(models.User.role == models.UserRole.admin, models.User.wsa_id.is_(None)).order_by(models.User.created_at).first()
        db.query(models.Notification).delete()
        db.query(models.ReportAssignment).delete()
        db.query(models.CitizenReport).delete()
        db.flush()
        now = datetime.now(timezone.utc)
        made = {}
        for i, (wsa_name, issue, text, days, state) in enumerate(REPORTS):
            wsa = db.query(models.WSA).filter(models.WSA.name == wsa_name).first()
            if wsa is None:
                print("  skipped (authority not found):", wsa_name)
                continue
            created = now - timedelta(days=days, hours=i % 7)
            report = models.CitizenReport(
                wsa_id=wsa.id, issue_type=ISSUE[issue], description=text, reference_code=f"HS-{uuid.uuid4().hex[:8].upper()}",
                case_status="open", lat=(wsa.lat or LAT_LNG_FALLBACK[0]) + (i % 5) * 0.004, lng=(wsa.lng or LAT_LNG_FALLBACK[1]) + (i % 4) * 0.004,
                created_at=created,
            )
            db.add(report)
            db.flush()
            made[state] = made.get(state, 0) + 1
            if state == "open":
                continue
            if state in ("review", "resolved") and admin:
                report.case_status = state if state == "resolved" else "in_review"
                report.reviewed_by = admin.id
                report.reviewed_at = created + timedelta(hours=5)
                if state == "resolved":
                    report.resolved_by, report.resolved_at = admin.id, created + timedelta(days=2)
                    report.admin_comment = "Repair checked on site and confirmed."
                continue
            # the rest have a ticket: pick a contractor set up for this authority and issue type
            contractor = next((c for c in db.query(models.Contractor).filter(models.Contractor.is_active).order_by(models.Contractor.name)
                               if helpers.can_serve(db, c.id, wsa.id, issue)), None)
            if contractor is None:
                print("  no contractor covers", wsa_name, issue)
                continue
            report.case_status = "in_review"
            report.reviewed_by, report.reviewed_at = (admin.id if admin else None), created + timedelta(hours=3)
            if state == "rejected_then_working":
                other = next((c for c in db.query(models.Contractor).filter(models.Contractor.is_active, models.Contractor.id != contractor.id)
                              if helpers.can_serve(db, c.id, wsa.id, issue)), None)
                if other:
                    db.add(models.ReportAssignment(report_id=report.id, contractor_id=other.id, assigned_by=admin.id if admin else None, status="rejected",
                           rejected_reason="No crew available in this area this week.", created_at=now - timedelta(days=3), closed_at=now - timedelta(days=2, hours=20),
                           due_at=now - timedelta(days=2)))
                    db.flush()
            status = {"assigned": "assigned", "accepted": "accepted", "working": "in_progress", "fixed": "fixed", "rejected_then_working": "in_progress"}[state]
            # tickets were handed out a few hours ago, so most are on time; the rejected-then-reassigned one is two days old and overdue on purpose
            given = now - (timedelta(days=2) if state == "rejected_then_working" else timedelta(hours=3 + i % 5))
            report.created_at = min(report.created_at, given - timedelta(hours=1))
            ticket = models.ReportAssignment(
                report_id=report.id, contractor_id=contractor.id, assigned_by=admin.id if admin else None, status=status,
                instructions="Isolate the section, repair, and photograph the finished work.", created_at=given,
                due_at=given + timedelta(hours=helpers.DEFAULT_DUE_HOURS[issue]),
            )
            if status != "assigned":
                ticket.accepted_at = given + timedelta(minutes=40)
            if status in ("in_progress", "fixed"):
                ticket.started_at = given + timedelta(hours=1)
            if status == "fixed":
                ticket.fixed_at = given + timedelta(hours=2)
                ticket.contractor_note = "Replaced the damaged section and tested pressure."
            db.add(ticket)
        added = add_history(db, admin, now)
        db.commit()
        print("seeded:", sum(made.values()), "reports", made, "plus", added, "past verified repairs for the contractor dashboard")
    finally:
        db.close()


if __name__ == "__main__":
    main("--apply" in sys.argv)
