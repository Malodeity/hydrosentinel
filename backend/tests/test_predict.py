"""
predict_wsa_risk decides which risk score citizens and admins see. Two ways
it can be wrong even with a working model: reporting a risk_level that
disagrees with what the model actually predicted (a real bug found while
building this — the old code derived risk_level from P(high) alone instead
of the model's argmax, so a confident "medium" prediction could be reported
as "low"), and trusting a low-confidence or feature-starved prediction
instead of falling back to the heuristic.
"""
import numpy as np

from ai.predict import predict_wsa_risk
from app.models import CAPStatus, ModelSource, RiskLevel, WSA


class FakeModel:
    """Stands in for XGBClassifier — returns fixed predict_proba output."""

    def __init__(self, probabilities: list[float]):
        self._probabilities = np.array([probabilities])

    def predict_proba(self, _features):
        return self._probabilities


def make_wsa(**overrides) -> WSA:
    defaults = dict(
        name="Test WSA", province="Gauteng", blue_drop_score=70.0, nrw_percent=20.0,
        maint_pct=5.0, cap_status=CAPStatus.none, risk_level=RiskLevel.low, lat=0.0, lng=0.0,
    )
    defaults.update(overrides)
    return WSA(**defaults)


def test_no_model_falls_back_to_heuristic():
    wsa = make_wsa()
    result = predict_wsa_risk(wsa, None)
    assert result["model_source"] == ModelSource.heuristic


def test_model_uses_argmax_not_high_class_probability_alone():
    # P(low)=0.1, P(medium)=0.65, P(high)=0.25 — argmax is medium, but the
    # old buggy code thresholded P(high)=0.25 alone and would report "low"
    wsa = make_wsa()
    model = FakeModel([0.10, 0.65, 0.25])

    result = predict_wsa_risk(wsa, model)

    assert result["risk_level"] == RiskLevel.medium
    assert result["model_source"] == ModelSource.xgboost


def test_confident_high_prediction_uses_model():
    wsa = make_wsa()
    model = FakeModel([0.05, 0.10, 0.85])

    result = predict_wsa_risk(wsa, model)

    assert result["risk_level"] == RiskLevel.high
    assert result["model_source"] == ModelSource.xgboost
    assert result["probability"] == 0.85


def test_low_confidence_prediction_falls_back_to_heuristic():
    # no class reaches the 0.5 confidence floor
    wsa = make_wsa()
    model = FakeModel([0.36, 0.34, 0.30])

    result = predict_wsa_risk(wsa, model)

    assert result["model_source"] == ModelSource.heuristic


def test_missing_blue_drop_score_falls_back_to_heuristic_even_with_model():
    wsa = make_wsa(blue_drop_score=None)
    model = FakeModel([0.05, 0.10, 0.85])  # would be a confident model prediction if used

    result = predict_wsa_risk(wsa, model)

    assert result["model_source"] == ModelSource.heuristic


def test_probability_is_clamped_below_one():
    wsa = make_wsa()
    model = FakeModel([0.0, 0.0, 1.0])

    result = predict_wsa_risk(wsa, model)

    assert result["probability"] <= 0.99
