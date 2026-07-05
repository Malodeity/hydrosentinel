from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ai.predict import predict_wsa_risk
from app import auth, models, schemas
from app.alert_helpers import raise_high_risk_alert
from app.audit_helpers import write_audit
from app.database import get_db

router = APIRouter(prefix="/risk", tags=["risk"])


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

    model = getattr(request.app.state, "risk_model", None)
    prediction = predict_wsa_risk(wsa, model)

    model_source = models.ModelSource.xgboost if model is not None else models.ModelSource.heuristic
    model_version = "xgboost_v1" if model is not None else "heuristic_v1"

    old_level = wsa.risk_level
    wsa.risk_level = prediction["risk_level"]
    db.add(wsa)

    db.add(models.RiskScoreHistory(
        wsa_id=wsa.id,
        risk_level=prediction["risk_level"],
        probability=prediction["probability"],
        model_source=model_source,
        model_version=model_version,
        scored_by=current_user.id,
    ))

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

    if prediction["risk_level"] == models.RiskLevel.high:
        raise_high_risk_alert(wsa, db)

    db.commit()
    db.refresh(wsa)

    return schemas.RiskScoreResponse(
        wsa_id=wsa.id,
        name=wsa.name,
        risk_level=wsa.risk_level,
        probability=prediction["probability"],
        model_source=model_source,
    )


@router.get("/scores", response_model=list[schemas.RiskScoreListItem])
def list_risk_scores(db: Session = Depends(get_db)) -> list[schemas.RiskScoreListItem]:
    wsas = db.query(models.WSA).order_by(models.WSA.name.asc()).all()
    return [
        schemas.RiskScoreListItem(wsa_id=wsa.id, name=wsa.name, risk_level=wsa.risk_level)
        for wsa in wsas
    ]


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
