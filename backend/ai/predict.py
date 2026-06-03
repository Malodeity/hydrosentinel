from pathlib import Path
from typing import Any

import joblib

from ai.features import build_feature_frame
from app.models import RiskLevel, WSA


def load_serialized_model(model_path: str | Path) -> Any | None:
    # this loads the saved model once at startup and returns None when no model file exists yet
    path = Path(model_path)
    if not path.exists():
        return None
    return joblib.load(path)


def _heuristic_probability(wsa: WSA) -> float:
    # this gives you a fallback risk score so the demo still works before a real model is trained
    score = 0.0
    score += max(0.0, 100.0 - float(wsa.blue_drop_score or 0.0)) * 0.35
    score += float(wsa.nrw_percent or 0.0) * 0.35
    score += max(0.0, 100.0 - float(wsa.maint_pct or 0.0)) * 0.20
    score += {"none": 10.0, "submitted": 7.0, "in_progress": 4.0, "completed": 1.0}[wsa.cap_status.value]
    return round(min(score / 100.0, 0.99), 4)


def _probability_to_risk(probability: float) -> RiskLevel:
    if probability >= 0.66:
        return RiskLevel.high
    if probability >= 0.33:
        return RiskLevel.medium
    return RiskLevel.low


def predict_wsa_risk(wsa: WSA, model: Any | None) -> dict[str, RiskLevel | float]:
    # this uses the trained model when it exists and falls back to the simple heuristic when it does not
    if model is None:
        probability = _heuristic_probability(wsa)
        return {"risk_level": _probability_to_risk(probability), "probability": probability}

    features = build_feature_frame(wsa)
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)[0]
        probability = float(probabilities[-1])
    else:
        probability = float(model.predict(features)[0])

    probability = max(0.0, min(probability, 0.99))
    return {"risk_level": _probability_to_risk(probability), "probability": round(probability, 4)}
