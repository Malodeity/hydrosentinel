from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ai.predict import predict_wsa_risk
from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/score/{wsa_id}", response_model=schemas.RiskScoreResponse)
def score_wsa_risk(
    wsa_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_admin_user),
) -> schemas.RiskScoreResponse:
    # this runs the model for one wsa and saves the new risk level back into the database
    wsa = db.query(models.WSA).filter(models.WSA.id == wsa_id).first()
    if not wsa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WSA not found")

    model = getattr(request.app.state, "risk_model", None)
    prediction = predict_wsa_risk(wsa, model)
    wsa.risk_level = prediction["risk_level"]
    db.add(wsa)
    db.commit()
    db.refresh(wsa)

    return schemas.RiskScoreResponse(
        wsa_id=wsa.id,
        name=wsa.name,
        risk_level=wsa.risk_level,
        probability=prediction["probability"],
    )


@router.get("/scores", response_model=list[schemas.RiskScoreListItem])
def list_risk_scores(db: Session = Depends(get_db)) -> list[schemas.RiskScoreListItem]:
    # this gives the frontend a lightweight list of current risk labels for every wsa
    wsas = db.query(models.WSA).order_by(models.WSA.name.asc()).all()
    return [
        schemas.RiskScoreListItem(wsa_id=wsa.id, name=wsa.name, risk_level=wsa.risk_level)
        for wsa in wsas
    ]
