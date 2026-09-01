from pathlib import Path
from typing import Any

import joblib

from ai.features import build_feature_frame
from ai.train import RISK_TO_TARGET
from app.models import ModelSource, RiskLevel, WSA

_TARGET_TO_RISK = {v: RiskLevel(k) for k, v in RISK_TO_TARGET.items()}

# below this confidence in the model's top predicted class, prefer the
# heuristic over a prediction the model itself isn't sure about
_CONFIDENCE_FLOOR = 0.5


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


def _heuristic_result(wsa: WSA) -> dict[str, RiskLevel | float | ModelSource]:
    probability = _heuristic_probability(wsa)
    return {"risk_level": _probability_to_risk(probability), "probability": probability, "model_source": ModelSource.heuristic}


def predict_wsa_risk(wsa: WSA, model: Any | None) -> dict[str, RiskLevel | float | ModelSource]:
    # falls back to the heuristic when there's no model, when a feature the
    # model actually relies on is missing (a model trained on real data
    # shouldn't be trusted on an all-defaulted feature row), or when the
    # model itself isn't confident in its top prediction
    if model is None or wsa.blue_drop_score is None:
        return _heuristic_result(wsa)

    features = build_feature_frame(wsa)
    probabilities = model.predict_proba(features)[0]
    predicted_index = int(probabilities.argmax())
    confidence = float(probabilities[predicted_index])

    if confidence < _CONFIDENCE_FLOOR:
        return _heuristic_result(wsa)

    confidence = min(confidence, 0.99)
    return {
        "risk_level": _TARGET_TO_RISK[predicted_index],
        "probability": round(confidence, 4),
        "model_source": ModelSource.xgboost,
    }
