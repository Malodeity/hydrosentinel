"""
Risk trajectory turns risk_score_history from a static snapshot into a
forecast: not just "this WSA is medium risk" but "this WSA is trending
toward high risk". A WSA whose last 3 scores rose 0.40 -> 0.55 -> 0.68 is a
materially different situation than one flat at 0.55, even though both
currently read "medium" -- the trend must survive that distinction.
"""
from ai.trajectory import compute_trajectory


def test_insufficient_history_reports_unknown_trend():
    result = compute_trajectory([0.5])
    assert result["trend"] == "insufficient_data"
    assert result["projected_risk_level"] is None


def test_flat_history_reports_stable_trend():
    result = compute_trajectory([0.50, 0.51, 0.49, 0.50])
    assert result["trend"] == "stable"


def test_rising_history_reports_worsening_trend():
    result = compute_trajectory([0.20, 0.35, 0.50, 0.64])
    assert result["trend"] == "worsening"
    assert result["projected_probability"] > result["current_probability"]


def test_falling_history_reports_improving_trend():
    result = compute_trajectory([0.80, 0.65, 0.50, 0.36])
    assert result["trend"] == "improving"
    assert result["projected_probability"] < result["current_probability"]


def test_projected_probability_is_clamped_to_valid_range():
    # a steep rise shouldn't extrapolate past 1.0 (or below 0.0 for a steep fall)
    result = compute_trajectory([0.10, 0.40, 0.70, 0.99])
    assert 0.0 <= result["projected_probability"] <= 1.0


def test_worsening_trend_flags_next_tier_crossing():
    # currently medium (0.55), rising fast enough to project into high (>=0.66)
    result = compute_trajectory([0.30, 0.42, 0.55])
    assert result["current_risk_level"] == "medium"
    assert result["projected_risk_level"] == "high"
    assert result["crosses_tier"] is True


def test_stable_trend_does_not_flag_tier_crossing():
    result = compute_trajectory([0.55, 0.56, 0.54, 0.55])
    assert result["crosses_tier"] is False
