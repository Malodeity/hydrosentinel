# Risk scoring API. Scoring itself lives in ai/predict.py; this file runs it, stores the history and raises alerts.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai.predict import predict_wsa_risk
from ai.trajectory import compute_trajectory
from app import auth, models, schemas
from app.alert_helpers import raise_high_risk_alert, raise_risk_increased_alert
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/risk", tags=["risk"])


# scores one authority and stages everything that follows from it: the new level on the authority, a history row (scored_by is None for the
# automatic run), and the 'high risk' / 'risk increased' alerts. the caller writes any audit entry and commits.
# used by the Score risk now button below and by the scheduled re-scoring in app/scheduler.py, so both behave the same
def record_score(wsa: models.WSA, model, db: Session, scored_by) -> dict:
    prediction = predict_wsa_risk(wsa, model)
    model_source = prediction["model_source"]
    old_level = wsa.risk_level
    wsa.risk_level = prediction["risk_level"]
    db.add(wsa)
    db.add(models.RiskScoreHistory(
        wsa_id=wsa.id,
        risk_level=prediction["risk_level"],
        probability=prediction["probability"],
        model_source=model_source,
        model_version="xgboost_v1" if model_source == models.ModelSource.xgboost else "heuristic_v1",
        scored_by=scored_by,
    ))
    if prediction["risk_level"] == models.RiskLevel.high:
        raise_high_risk_alert(wsa, db)
    raise_risk_increased_alert(wsa, old_level, db)
    return prediction


# POST /risk/score/{id} (admin): scores one authority with the XGBoost model (or the fallback rule), saves the result to its history,
# raises 'high risk' / 'risk increased' alerts, and writes an audit entry.
@router.post("/score/{wsa_id}", response_model=schemas.RiskScoreResponse)
def score_wsa_risk(
    wsa_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
) -> schemas.RiskScoreResponse:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    auth.require_wsa_access(current_user, wsa.id)

    old_level = wsa.risk_level
    prediction = record_score(wsa, getattr(request.app.state, "risk_model", None), db, current_user.id)
    model_source = prediction["model_source"]

    write_audit(
        db=db,
        user_id=current_user.id,
        action=models.AuditAction.risk_score_run,
        table_name="wsa",
        record_id=wsa.id,
        old_value={"risk_level": old_level.value},
        new_value={"risk_level": prediction["risk_level"].value, "probability": prediction["probability"], "model_source": model_source.value},
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(wsa)

    return schemas.RiskScoreResponse(
        wsa_id=wsa.id,
        name=wsa.name,
        risk_level=wsa.risk_level,
        probability=prediction["probability"],
        model_source=model_source,
    )


# admin: how the automatic re-scoring is set up and when it last ran, shown beside the Score risk now button
@router.get("/schedule", response_model=schemas.RiskSchedule)
def get_risk_schedule(db: Session = Depends(get_db), _: models.User = Depends(auth.get_current_admin_user)) -> dict:
    from app.config import settings

    last = db.query(func.max(models.RiskScoreHistory.scored_at)).filter(models.RiskScoreHistory.scored_by.is_(None)).scalar()
    return {"interval_hours": settings.rescore_interval_hours, "last_automatic_run": last}


# public: the current risk level of every authority (the colours on the map come from this)
@router.get("/scores", response_model=list[schemas.RiskScoreListItem])
def list_risk_scores(db: Session = Depends(get_db)) -> list[schemas.RiskScoreListItem]:
    wsas = db.query(models.WSA).order_by(models.WSA.name.asc()).all()
    return [
        schemas.RiskScoreListItem(wsa_id=wsa.id, name=wsa.name, risk_level=wsa.risk_level)
        for wsa in wsas
    ]


# admin only: every score run for one authority, newest first (the history table and sparkline on the CAP tab)
@router.get("/history/{wsa_id}", response_model=list[schemas.RiskScoreHistoryRead])
def get_risk_history(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[models.RiskScoreHistory]:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")
    return (
        db.query(models.RiskScoreHistory)
        .filter(models.RiskScoreHistory.wsa_id == wsa_id)
        .order_by(models.RiskScoreHistory.scored_at.desc())
        .all()
    )


# admin only: fits a straight line through one authority's score history and projects the next score (see ai/trajectory.py)
@router.get("/trajectory/{wsa_id}", response_model=schemas.RiskTrajectoryResponse)
def get_risk_trajectory(
    wsa_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.RiskTrajectoryResponse:
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")

    history = (
        db.query(models.RiskScoreHistory)
        .filter(models.RiskScoreHistory.wsa_id == wsa_id)
        .order_by(models.RiskScoreHistory.scored_at.asc())
        .all()
    )
    probabilities = [float(entry.probability) for entry in history]
    trajectory = compute_trajectory(probabilities)

    return schemas.RiskTrajectoryResponse(
        wsa_id=wsa.id,
        name=wsa.name,
        sample_size=len(probabilities),
        **trajectory,
    )


# GET /risk/trending (admin): authorities projected to cross into a worse risk level. feeds Overview > 'Trending toward higher risk'.
@router.get("/trending", response_model=list[schemas.RiskTrajectoryResponse])
def list_trending_wsas(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> list[schemas.RiskTrajectoryResponse]:
    # early-warning list: every WSA whose trend is projected to cross into a
    # worse risk tier before it's actually scored there
    results: list[schemas.RiskTrajectoryResponse] = []
    wsas = db.query(models.WSA).all()
    for wsa in wsas:
        history = (
            db.query(models.RiskScoreHistory)
            .filter(models.RiskScoreHistory.wsa_id == wsa.id)
            .order_by(models.RiskScoreHistory.scored_at.asc())
            .all()
        )
        probabilities = [float(entry.probability) for entry in history]
        trajectory = compute_trajectory(probabilities)
        if trajectory["crosses_tier"]:
            results.append(schemas.RiskTrajectoryResponse(wsa_id=wsa.id, name=wsa.name, sample_size=len(probabilities), **trajectory))
    return results
