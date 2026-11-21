# Contractors and repair tickets. Admin side: manage contractors and where they work, assign a report to one (single or several at once),
# review finished work (verify / send back / cancel). Contractor side: see own tickets and accept, reject, start or mark fixed.
# Everyone: the notification bell. Rules (who may be assigned, status steps, due dates) live in app/assignment_helpers.py.

from uuid import UUID

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import assignment_helpers as helpers
from app import auth, models, schemas
from app.audit_helpers import write_audit
from app.database import get_db
from app.routes import reports as reports_routes
from app.routes.reports import photo_urls_for, repair_photo_urls_for

router = APIRouter(tags=["assignments"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------------------------------------------------
# builders: database rows -> API shapes
# ---------------------------------------------------------------------------------------------------------------------
def _assignment_read(ticket: models.ReportAssignment) -> schemas.AssignmentRead:
    report = ticket.report
    base = helpers.summarize(ticket).model_dump()
    return schemas.AssignmentRead(
        **base,
        report_id=report.id,
        wsa_id=report.wsa_id,
        wsa_name=report.wsa.name,
        reference_code=report.reference_code,
        issue_type=report.issue_type,
        description=report.description,
        lat=report.lat,
        lng=report.lng,
        photo_urls=photo_urls_for(report),
        repair_photo_urls=repair_photo_urls_for(ticket),
        instructions=ticket.instructions,
        admin_note=ticket.admin_note,
        created_at=ticket.created_at,
        accepted_at=ticket.accepted_at,
        started_at=ticket.started_at,
        fixed_at=ticket.fixed_at,
        closed_at=ticket.closed_at,
    )


def _contractor_read(db: Session, contractor: models.Contractor, only_wsa: UUID | None = None) -> schemas.ContractorRead:
    rows = [row for row in contractor.coverage if only_wsa is None or row.wsa_id == only_wsa]
    open_tickets = (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.contractor_id == contractor.id, models.ReportAssignment.status.in_(helpers.ACTIVE))
        .count()
    )
    return schemas.ContractorRead(
        id=contractor.id,
        name=contractor.name,
        contact_name=contractor.contact_name,
        phone=contractor.phone,
        email=contractor.email,
        is_active=contractor.is_active,
        coverage=[
            schemas.CoverageRead(wsa_id=row.wsa_id, wsa_name=row.wsa.name, issue_types=sorted(helpers.coverage_issue_types(row)))
            for row in rows
        ],
        open_tickets=open_tickets,
    )


def _get_contractor(db: Session, contractor_id: UUID) -> models.Contractor:
    contractor = db.query(models.Contractor).filter(models.Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")
    return contractor


def _get_report(db: Session, report_id: UUID) -> models.CitizenReport:
    report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def _get_ticket(db: Session, assignment_id: UUID) -> models.ReportAssignment:
    ticket = db.query(models.ReportAssignment).filter(models.ReportAssignment.id == assignment_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


# ---------------------------------------------------------------------------------------------------------------------
# contractor directory (admin)
# ---------------------------------------------------------------------------------------------------------------------
# GET /contractors: the contractors an admin can assign. an admin tied to one authority sees contractors working for it, plus new ones with no area yet
@router.get("/contractors", response_model=list[schemas.ContractorRead])
def list_contractors(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.ContractorRead]:
    contractors = db.query(models.Contractor).order_by(models.Contractor.name.asc()).all()
    scope = current_user.wsa_id
    if scope is not None:
        contractors = [c for c in contractors if not c.coverage or any(row.wsa_id == scope for row in c.coverage)]
    return [_contractor_read(db, c, only_wsa=scope) for c in contractors]


# POST /contractors: add a contractor company
@router.post("/contractors", response_model=schemas.ContractorRead, status_code=status.HTTP_201_CREATED)
def create_contractor(
    payload: schemas.ContractorWrite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.ContractorRead:
    if db.query(models.Contractor).filter(models.Contractor.name.ilike(payload.name.strip())).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A contractor with this name already exists")
    contractor = models.Contractor(
        name=payload.name.strip(),
        contact_name=payload.contact_name,
        phone=payload.phone,
        email=payload.email,
        is_active=payload.is_active,
    )
    db.add(contractor)
    db.flush()
    write_audit(db, current_user.id, models.AuditAction.contractor_saved, "contractors", contractor.id,
                None, {"name": contractor.name, "is_active": contractor.is_active}, _ip(request))
    db.commit()
    db.refresh(contractor)
    return _contractor_read(db, contractor, only_wsa=current_user.wsa_id)


# PATCH /contractors/{id}: edit details or switch a contractor off. switching off stops new tickets only; tickets it already holds stay with it and it can finish them
@router.patch("/contractors/{contractor_id}", response_model=schemas.ContractorRead)
def update_contractor(
    contractor_id: UUID,
    payload: schemas.ContractorWrite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.ContractorRead:
    contractor = _get_contractor(db, contractor_id)
    # an authority admin may only edit contractors that work for their authority (or have no area yet)
    if current_user.wsa_id is not None and contractor.coverage and not any(r.wsa_id == current_user.wsa_id for r in contractor.coverage):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This contractor does not work for your authority")
    clash = db.query(models.Contractor).filter(models.Contractor.name.ilike(payload.name.strip()), models.Contractor.id != contractor.id).first()
    if clash:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A contractor with this name already exists")
    old = {"name": contractor.name, "is_active": contractor.is_active}
    contractor.name = payload.name.strip()
    contractor.contact_name = payload.contact_name
    contractor.phone = payload.phone
    contractor.email = payload.email
    contractor.is_active = payload.is_active
    write_audit(db, current_user.id, models.AuditAction.contractor_saved, "contractors", contractor.id,
                old, {"name": contractor.name, "is_active": contractor.is_active}, _ip(request))
    db.commit()
    db.refresh(contractor)
    return _contractor_read(db, contractor, only_wsa=current_user.wsa_id)


# PUT /contractors/{id}/coverage: say which authority and issue types this contractor works on (adds or replaces that authority's row)
@router.put("/contractors/{contractor_id}/coverage", response_model=schemas.ContractorRead)
def set_coverage(
    contractor_id: UUID,
    payload: schemas.CoverageWrite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.ContractorRead:
    contractor = _get_contractor(db, contractor_id)
    auth.require_wsa_access(current_user, payload.wsa_id)
    if not db.query(models.WSA).filter(models.WSA.id == payload.wsa_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    issues = ",".join(sorted({item.value for item in payload.issue_types}))
    row = next((r for r in contractor.coverage if r.wsa_id == payload.wsa_id), None)
    old = {"issue_types": row.issue_types} if row else None
    if row:
        row.issue_types = issues
    else:
        db.add(models.ContractorCoverage(contractor_id=contractor.id, wsa_id=payload.wsa_id, issue_types=issues))
    write_audit(db, current_user.id, models.AuditAction.contractor_saved, "contractors", contractor.id,
                old, {"wsa_id": str(payload.wsa_id), "issue_types": issues}, _ip(request))
    db.commit()
    db.refresh(contractor)
    return _contractor_read(db, contractor, only_wsa=current_user.wsa_id)


# DELETE /contractors/{id}/coverage/{wsa_id}: stop a contractor working for an authority. refused while it still holds open tickets there
@router.delete("/contractors/{contractor_id}/coverage/{wsa_id}", response_model=schemas.ContractorRead)
def remove_coverage(
    contractor_id: UUID,
    wsa_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.ContractorRead:
    contractor = _get_contractor(db, contractor_id)
    auth.require_wsa_access(current_user, wsa_id)
    row = next((r for r in contractor.coverage if r.wsa_id == wsa_id), None)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This contractor does not work for that authority")
    open_here = (
        db.query(models.ReportAssignment)
        .join(models.CitizenReport, models.CitizenReport.id == models.ReportAssignment.report_id)
        .filter(
            models.ReportAssignment.contractor_id == contractor.id,
            models.CitizenReport.wsa_id == wsa_id,
            models.ReportAssignment.status.in_(helpers.ACTIVE),
        )
        .count()
    )
    if open_here:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{open_here} open ticket(s) must be finished or reassigned first")
    db.delete(row)
    write_audit(db, current_user.id, models.AuditAction.contractor_saved, "contractors", contractor.id,
                {"wsa_id": str(wsa_id), "issue_types": row.issue_types}, {"wsa_id": str(wsa_id), "issue_types": None}, _ip(request))
    db.commit()
    db.refresh(contractor)
    return _contractor_read(db, contractor, only_wsa=current_user.wsa_id)


# GET /contractors/performance: how each contractor is doing. for the admin to look at; it is not used to score authorities or train the model
@router.get("/contractors/performance", response_model=list[schemas.ContractorPerformance])
def contractor_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.ContractorPerformance]:
    query = db.query(models.ReportAssignment).join(models.CitizenReport, models.CitizenReport.id == models.ReportAssignment.report_id)
    if current_user.wsa_id is not None:
        query = query.filter(models.CitizenReport.wsa_id == current_user.wsa_id)
    by_contractor: dict[UUID, list[models.ReportAssignment]] = {}
    for ticket in query.all():
        by_contractor.setdefault(ticket.contractor_id, []).append(ticket)

    rows: list[schemas.ContractorPerformance] = []
    for contractor_id, tickets in by_contractor.items():
        done = [t for t in tickets if t.fixed_at is not None]
        on_time = [t for t in done if t.due_at is None or t.fixed_at <= t.due_at]
        hours = [(t.fixed_at - t.created_at).total_seconds() / 3600 for t in done]
        rows.append(schemas.ContractorPerformance(
            contractor_id=contractor_id,
            name=tickets[0].contractor.name,
            total=len(tickets),
            open=sum(1 for t in tickets if t.status in helpers.ACTIVE),
            overdue=sum(1 for t in tickets if helpers.is_overdue(t)),
            fixed=len(done),
            rejected=sum(1 for t in tickets if t.status == "rejected"),
            fixed_on_time_pct=round(100 * len(on_time) / len(done), 1) if done else None,
            avg_hours_to_fix=round(sum(hours) / len(hours), 1) if hours else None,
        ))
    return sorted(rows, key=lambda r: r.name)


# ---------------------------------------------------------------------------------------------------------------------
# assigning (admin)
# ---------------------------------------------------------------------------------------------------------------------
def _check_assignable(db: Session, report: models.CitizenReport, contractor: models.Contractor, user: models.User) -> None:
    auth.require_wsa_access(user, report.wsa_id)
    if report.case_status == "resolved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This report is already resolved")
    if not contractor.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This contractor is switched off")
    if not helpers.can_serve(db, contractor.id, report.wsa_id, report.issue_type.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{contractor.name} is not set up for {report.issue_type.value} reports in this authority",
        )


def _assign(db: Session, report: models.CitizenReport, contractor: models.Contractor, payload: schemas.AssignRequest,
            user: models.User, ip: str | None) -> models.ReportAssignment:
    # hands the report to the contractor. an earlier open ticket on the same report is cancelled (that is what "reassign" means)
    if payload.due_at is not None and payload.due_at <= helpers.now():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The due date must be in the future")

    previous = helpers.active_assignment(db, report.id)
    if previous is not None:
        previous.status = "cancelled"
        previous.closed_at = helpers.now()
        previous.admin_note = "Reassigned"
        db.add(previous)
        db.flush()  # the old ticket must leave the active set before the new one is inserted (one active ticket per report, enforced by the database)
        helpers.notify(db, helpers.contractor_users(db, previous.contractor_id), "Ticket reassigned",
                       f"Report {report.reference_code} was given to another contractor.", previous)

    ticket = models.ReportAssignment(
        report_id=report.id,
        contractor_id=contractor.id,
        assigned_by=user.id,
        status="assigned",
        instructions=payload.instructions.strip() if payload.instructions else None,
        due_at=payload.due_at or helpers.default_due(report.issue_type.value),
    )
    db.add(ticket)
    db.flush()

    if report.case_status == "open":
        report.case_status = "in_review"
        report.reviewed_by = user.id
        report.reviewed_at = helpers.now()
        db.add(report)
        write_audit(db, user.id, models.AuditAction.report_status_updated, "citizen_reports", report.id,
                    {"case_status": "open"}, {"case_status": "in_review", "reason": "assigned to a contractor"}, ip)

    write_audit(db, user.id, models.AuditAction.report_assigned, "report_assignments", ticket.id,
                {"contractor": previous.contractor.name} if previous else None,
                {"report": report.reference_code, "contractor": contractor.name, "due_at": ticket.due_at.isoformat()}, ip)
    helpers.notify(
        db, helpers.contractor_users(db, contractor.id), f"New ticket {report.reference_code}",
        f"{report.issue_type.value.title()} in {report.wsa.name}. Due {ticket.due_at:%d %b %Y %H:%M}.", ticket,
    )
    return ticket


# POST /reports/assign-bulk: give several reports to one contractor in one go. all-or-nothing: if any report cannot be assigned, none is
@router.post("/reports/assign-bulk", response_model=list[schemas.AssignmentRead], status_code=status.HTTP_201_CREATED)
def assign_bulk(
    payload: schemas.BulkAssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.AssignmentRead]:
    contractor = _get_contractor(db, payload.contractor_id)
    reports = []
    problems = []
    for report_id in dict.fromkeys(payload.report_ids):
        report = db.query(models.CitizenReport).filter(models.CitizenReport.id == report_id).first()
        if report is None:
            problems.append({"report_id": str(report_id), "reason": "Report not found"})
            continue
        try:
            _check_assignable(db, report, contractor, current_user)
            reports.append(report)
        except HTTPException as exc:
            problems.append({"report_id": str(report_id), "reason": exc.detail})
    if problems:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problems)
    try:
        tickets = [_assign(db, report, contractor, payload, current_user, _ip(request)) for report in reports]
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Someone else just assigned one of these reports. Reload and try again.")
    return [_assignment_read(t) for t in tickets]


# POST /reports/{id}/assign: give one report to a contractor (or hand it to a different one)
@router.post("/reports/{report_id}/assign", response_model=schemas.AssignmentRead, status_code=status.HTTP_201_CREATED)
def assign_report(
    report_id: UUID,
    payload: schemas.AssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AssignmentRead:
    report = _get_report(db, report_id)
    contractor = _get_contractor(db, payload.contractor_id)
    _check_assignable(db, report, contractor, current_user)
    try:
        ticket = _assign(db, report, contractor, payload, current_user, _ip(request))
        db.commit()
    except IntegrityError:
        # two admins assigned the same report at the same moment: the database allowed only one
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Someone else just assigned this report. Reload and check the ticket.")
    db.refresh(ticket)
    return _assignment_read(ticket)


# GET /reports/{id}/assignments: every ticket the report has had, newest first
@router.get("/reports/{report_id}/assignments", response_model=list[schemas.AssignmentRead])
def report_assignments(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.AssignmentRead]:
    report = _get_report(db, report_id)
    auth.require_wsa_access(current_user, report.wsa_id)
    tickets = (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.report_id == report.id)
        .order_by(models.ReportAssignment.created_at.desc())
        .all()
    )
    return [_assignment_read(t) for t in tickets]


# GET /assignments: all tickets for the admin's view (optionally one status)
@router.get("/assignments", response_model=list[schemas.AssignmentRead])
def list_assignments(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.AssignmentRead]:
    query = db.query(models.ReportAssignment).join(models.CitizenReport, models.CitizenReport.id == models.ReportAssignment.report_id)
    if current_user.wsa_id is not None:
        query = query.filter(models.CitizenReport.wsa_id == current_user.wsa_id)
    if status_filter:
        query = query.filter(models.ReportAssignment.status == status_filter)
    return [_assignment_read(t) for t in query.order_by(models.ReportAssignment.created_at.desc()).all()]


# PATCH /assignments/{id}/review: the authority checks finished work. verify = it is fixed (this resolves the report); send_back = not good enough; cancel = stop the ticket
@router.patch("/assignments/{assignment_id}/review", response_model=schemas.AssignmentRead)
def review_assignment(
    assignment_id: UUID,
    payload: schemas.TicketReview,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.AssignmentRead:
    ticket = _get_ticket(db, assignment_id)
    report = ticket.report
    auth.require_wsa_access(current_user, report.wsa_id)
    note = payload.note.strip() if payload.note else None
    old = {"status": ticket.status}
    ip = _ip(request)
    contractor_staff = helpers.contractor_users(db, ticket.contractor_id)

    if payload.action == "verify":
        if ticket.status != "fixed":
            raise helpers.bad_step("verify", ticket.status)
        ticket.status = "closed"
        ticket.closed_at = helpers.now()
        ticket.admin_note = note or ticket.admin_note
        if report.case_status != "resolved":
            write_audit(db, current_user.id, models.AuditAction.report_status_updated, "citizen_reports", report.id,
                        {"case_status": report.case_status}, {"case_status": "resolved", "reason": "repair verified"}, ip)
            report.case_status = "resolved"
            report.resolved_by = current_user.id
            report.resolved_at = helpers.now()
            if note and not report.admin_comment:
                report.admin_comment = note
            db.add(report)
        helpers.notify(db, contractor_staff, f"Ticket {report.reference_code} verified", "The authority confirmed the repair. Thank you.", ticket)
    elif payload.action == "send_back":
        if ticket.status != "fixed":
            raise helpers.bad_step("send back", ticket.status)
        ticket.status = "sent_back"
        ticket.admin_note = note
        helpers.notify(db, contractor_staff, f"Ticket {report.reference_code} sent back", note, ticket)
    else:
        if ticket.status not in helpers.ACTIVE:
            raise helpers.bad_step("cancel", ticket.status)
        ticket.status = "cancelled"
        ticket.closed_at = helpers.now()
        ticket.admin_note = note
        helpers.notify(db, contractor_staff, f"Ticket {report.reference_code} cancelled", note or "The authority cancelled this ticket.", ticket)

    write_audit(db, current_user.id, models.AuditAction.assignment_updated, "report_assignments", ticket.id,
                old, {"status": ticket.status, "action": payload.action, "note": note}, ip)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _assignment_read(ticket)


# ---------------------------------------------------------------------------------------------------------------------
# contractor side
# ---------------------------------------------------------------------------------------------------------------------
def _own_ticket(db: Session, assignment_id: UUID, user: models.User) -> models.ReportAssignment:
    # a ticket that belongs to another contractor looks exactly like one that does not exist (404, not 403), so ids cannot be probed
    ticket = (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.id == assignment_id, models.ReportAssignment.contractor_id == user.contractor_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


# GET /my/tickets: the signed-in contractor's own tickets, newest first. a contractor switched off by the authority still sees and can finish tickets it already holds
@router.get("/my/tickets", response_model=list[schemas.AssignmentRead])
def my_tickets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_contractor),
) -> list[schemas.AssignmentRead]:
    tickets = (
        db.query(models.ReportAssignment)
        .filter(models.ReportAssignment.contractor_id == current_user.contractor_id)
        .order_by(models.ReportAssignment.created_at.desc())
        .all()
    )
    return [_assignment_read(t) for t in tickets]


# PATCH /my/tickets/{id}: accept, reject (with a reason), start, or mark fixed (with a note on what was done). the contractor can never resolve the report
@router.patch("/my/tickets/{assignment_id}", response_model=schemas.AssignmentRead)
def update_my_ticket(
    assignment_id: UUID,
    payload: schemas.TicketAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_contractor),
) -> schemas.AssignmentRead:
    ticket = _own_ticket(db, assignment_id, current_user)
    allowed_from, new_status = helpers.CONTRACTOR_STEPS[payload.action]
    if ticket.status not in allowed_from:
        raise helpers.bad_step(payload.action, ticket.status)

    old = {"status": ticket.status}
    note = payload.note.strip() if payload.note else None
    now = helpers.now()
    ticket.status = new_status
    if payload.action == "accept":
        ticket.accepted_at = now
    elif payload.action == "start":
        ticket.started_at = now
    elif payload.action == "reject":
        ticket.rejected_reason = note
        ticket.closed_at = now
    elif payload.action == "fix":
        ticket.contractor_note = note
        ticket.fixed_at = now

    report = ticket.report
    titles = {
        "accept": f"Ticket {report.reference_code} accepted",
        "reject": f"Ticket {report.reference_code} rejected",
        "start": f"Work started on {report.reference_code}",
        "fix": f"Ticket {report.reference_code} marked fixed",
    }
    body = {"reject": f"Reason: {note}", "fix": f"Contractor says: {note}. Please check and verify."}.get(payload.action)
    helpers.notify(db, helpers.admins_for_wsa(db, report.wsa_id), titles[payload.action], body, ticket)
    write_audit(db, current_user.id, models.AuditAction.assignment_updated, "report_assignments", ticket.id,
                old, {"status": new_status, "action": payload.action, "note": note}, _ip(request))
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _assignment_read(ticket)


# the contractor can attach "after" photos while the job is still theirs or waiting for the check. at most 8 per ticket, 5 MB each, images only
_PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_REPAIR_PHOTOS = 8
_MAX_PHOTO_BYTES = 5 * 1024 * 1024


# POST /my/tickets/{id}/photos: adds the contractor's repair photos to the ticket. the authority sees them when it checks the work
@router.post("/my/tickets/{assignment_id}/photos", response_model=schemas.AssignmentRead)
async def add_repair_photos(
    assignment_id: UUID,
    request: Request,
    photos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_contractor),
) -> schemas.AssignmentRead:
    ticket = _own_ticket(db, assignment_id, current_user)
    if ticket.status not in ("accepted", "in_progress", "sent_back", "fixed"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Accept the ticket before adding photos")
    folder = reports_routes.UPLOAD_ROOT / str(ticket.report_id) / "repair" / str(ticket.id)
    existing = len(repair_photo_urls_for(ticket))
    saved = 0
    for photo in photos:
        if Path(photo.filename or "").suffix.lower() not in _PHOTO_TYPES:
            continue
        data = await photo.read()
        if len(data) > _MAX_PHOTO_BYTES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A photo is larger than 5 MB")
        if existing + saved >= _MAX_REPAIR_PHOTOS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"At most {_MAX_REPAIR_PHOTOS} photos per ticket")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{uuid.uuid4()}{Path(photo.filename).suffix.lower()}").write_bytes(data)
        saved += 1
    if saved == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Attach at least one image (jpg, png, webp or gif)")
    write_audit(db, current_user.id, models.AuditAction.assignment_updated, "report_assignments", ticket.id,
                None, {"action": "repair_photos_added", "count": saved}, _ip(request))
    db.commit()
    return _assignment_read(ticket)


# ---------------------------------------------------------------------------------------------------------------------
# notifications: the bell, for every kind of user
# ---------------------------------------------------------------------------------------------------------------------
# GET /notifications: my messages, newest first
@router.get("/notifications", response_model=list[schemas.NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> list[models.Notification]:
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(50)
        .all()
    )


# POST /notifications/read-all: mark all of mine as read
@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> None:
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id, models.Notification.read_at.is_(None)
    ).update({"read_at": helpers.now()})
    db.commit()


# PATCH /notifications/{id}/read: mark one of mine as read (someone else's looks like it does not exist)
@router.patch("/notifications/{notification_id}/read", response_model=schemas.NotificationRead)
def read_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> models.Notification:
    item = db.query(models.Notification).filter(
        models.Notification.id == notification_id, models.Notification.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if item.read_at is None:
        item.read_at = helpers.now()
        db.commit()
        db.refresh(item)
    return item
