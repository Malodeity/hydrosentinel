# Repair-ticket rules in one place: who may be assigned, the status steps, due dates, notifications and the overdue check.
# Routes (routes/assignments.py, routes/reports.py) call these so the rules cannot drift apart.

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import mailer, models, schemas

ACTIVE = ("assigned", "accepted", "in_progress", "sent_back", "fixed")
WORKING = ("assigned", "accepted", "in_progress", "sent_back")  # still with the contractor: these can become overdue

# default hours to attend to each kind of report when the admin sets no due date (a target, not a contract term)
DEFAULT_DUE_HOURS = {"leak": 24, "outage": 24, "quality": 48, "billing": 72}

# what the contractor may do from each status
CONTRACTOR_STEPS = {
    "accept": ({"assigned"}, "accepted"),
    "reject": ({"assigned"}, "rejected"),
    "start": ({"accepted", "sent_back"}, "in_progress"),
    "fix": ({"accepted", "in_progress", "sent_back"}, "fixed"),
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def coverage_issue_types(row: models.ContractorCoverage) -> set[str]:
    return {item for item in row.issue_types.split(",") if item}


def can_serve(db: Session, contractor_id, wsa_id, issue_type: str) -> bool:
    # a contractor may only get tickets for an authority and issue type it is set up for
    row = (
        db.query(models.ContractorCoverage)
        .filter(models.ContractorCoverage.contractor_id == contractor_id, models.ContractorCoverage.wsa_id == wsa_id)
        .first()
    )
    return bool(row) and issue_type in coverage_issue_types(row)


def active_assignment(db: Session, report_id) -> models.ReportAssignment | None:
    return (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.report_id == report_id, models.ReportAssignment.status.in_(ACTIVE))
        .order_by(models.ReportAssignment.created_at.desc())
        .first()
    )


def latest_assignment(db: Session, report_id) -> models.ReportAssignment | None:
    return (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.report_id == report_id)
        .order_by(models.ReportAssignment.created_at.desc())
        .first()
    )


def is_overdue(assignment: models.ReportAssignment) -> bool:
    return assignment.status in WORKING and assignment.due_at is not None and assignment.due_at < now()


def notify(db: Session, users: list[models.User], title: str, body: str | None, assignment: models.ReportAssignment | None = None) -> None:
    # one bell message per user, plus an email when the server has mail settings. the caller commits
    for user in users:
        if not user.is_active:
            continue
        db.add(models.Notification(user_id=user.id, title=title, body=body, assignment_id=assignment.id if assignment else None))
        mailer.send_email(user.email, f"HydroSentinel: {title}", body or title)


def contractor_users(db: Session, contractor_id) -> list[models.User]:
    return db.query(models.User).filter(models.User.contractor_id == contractor_id, models.User.role == models.UserRole.contractor).all()


def admins_for_wsa(db: Session, wsa_id) -> list[models.User]:
    # national admins plus the admin tied to this authority
    return (
        db.query(models.User)
        .filter(models.User.role == models.UserRole.admin, (models.User.wsa_id.is_(None)) | (models.User.wsa_id == wsa_id))
        .all()
    )


def close_active_for_report(db: Session, report: models.CitizenReport, note: str) -> None:
    # an admin resolving a report by hand ends any open ticket on it, so no contractor keeps working a closed report
    for ticket in db.query(models.ReportAssignment).filter(
        models.ReportAssignment.report_id == report.id, models.ReportAssignment.status.in_(ACTIVE)
    ):
        ticket.status = "closed"
        ticket.closed_at = now()
        ticket.admin_note = ticket.admin_note or note
        db.add(ticket)
        notify(db, contractor_users(db, ticket.contractor_id), "Ticket closed", f"Report {report.reference_code} was closed by the authority.", ticket)


def default_due(issue_type: str) -> datetime:
    return now() + timedelta(hours=DEFAULT_DUE_HOURS.get(issue_type, 48))


def bad_step(action: str, current: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot {action} a ticket that is {current.replace('_', ' ')}")


def summarize(assignment: models.ReportAssignment) -> schemas.AssignmentSummary:
    return schemas.AssignmentSummary(
        id=assignment.id,
        status=assignment.status,
        contractor_id=assignment.contractor_id,
        contractor_name=assignment.contractor.name,
        due_at=assignment.due_at,
        overdue=is_overdue(assignment),
        contractor_note=assignment.contractor_note,
        rejected_reason=assignment.rejected_reason,
    )


def public_repair_status(assignment: models.ReportAssignment | None) -> str | None:
    # what a resident may see: progress only, never the company or its contact details
    if assignment is None:
        return None
    return {
        "assigned": "assigned",
        "accepted": "assigned",
        "sent_back": "in_progress",
        "in_progress": "in_progress",
        "fixed": "awaiting_check",
    }.get(assignment.status)
