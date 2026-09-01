import numpy as np

from ai.predict import _probability_to_risk

# a trend is only worth reporting if it moves at least this much per step —
# otherwise noise in the heuristic/model scoring reads as a false trend
_STABLE_SLOPE_THRESHOLD = 0.03


def compute_trajectory(probabilities: list[float]) -> dict:
    """
    Fits a simple linear trend across a WSA's risk_score_history probabilities
    (oldest first) and projects one step ahead. This is what turns
    risk_score_history from a log into a forecast: two WSAs can both read
    "medium" today while one is rising toward high and the other is flat.
    """
    if len(probabilities) < 2:
        return {
            "trend": "insufficient_data",
            "current_probability": probabilities[-1] if probabilities else None,
            "current_risk_level": _probability_to_risk(probabilities[-1]).value if probabilities else None,
            "projected_probability": None,
            "projected_risk_level": None,
            "crosses_tier": False,
        }

    x = np.arange(len(probabilities))
    slope, intercept = np.polyfit(x, probabilities, 1)
    projected = float(np.clip(slope * len(probabilities) + intercept, 0.0, 1.0))

    if slope > _STABLE_SLOPE_THRESHOLD:
        trend = "worsening"
    elif slope < -_STABLE_SLOPE_THRESHOLD:
        trend = "improving"
    else:
        trend = "stable"

    current = probabilities[-1]
    current_risk = _probability_to_risk(current)
    projected_risk = _probability_to_risk(projected)

    return {
        "trend": trend,
        "current_probability": round(current, 4),
        "current_risk_level": current_risk.value,
        "projected_probability": round(projected, 4),
        "projected_risk_level": projected_risk.value,
        "crosses_tier": trend == "worsening" and projected_risk != current_risk,
    }
