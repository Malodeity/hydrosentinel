# Turns an authority row into the six numbers the XGBoost model uses. The column ORDER here must match the order the saved model was trained with.

from collections.abc import Iterable

import pandas as pd

from app.models import CAPStatus, WSA

# the six inputs the xgboost model is trained on and scores with. the order matters: the model was trained with exactly this column order
FEATURE_COLUMNS = [
    "blue_drop_score",
    "nrw_percent",
    "maint_pct",
    "cap_status_code",
    "lat",
    "lng",
]

# xgboost needs numbers, so the cap status becomes 0 (none) up to 3 (completed)
CAP_STATUS_TO_CODE = {
    CAPStatus.none: 0,
    CAPStatus.submitted: 1,
    CAPStatus.in_progress: 2,
    CAPStatus.completed: 3,
}


# turns one authority row into the six numbers. a missing value becomes 0.0 here; ai/predict.py separately refuses to trust
# the model when the blue drop score is missing, so a made-up zero never drives a prediction
def wsa_to_feature_dict(wsa: WSA) -> dict[str, float]:
    return {
        "blue_drop_score": float(wsa.blue_drop_score or 0.0),
        "nrw_percent": float(wsa.nrw_percent or 0.0),
        "maint_pct": float(wsa.maint_pct or 0.0),
        "cap_status_code": float(CAP_STATUS_TO_CODE[wsa.cap_status]),
        "lat": float(wsa.lat),
        "lng": float(wsa.lng),
    }


def build_feature_frame(wsas: WSA | Iterable[WSA]) -> pd.DataFrame:
    if isinstance(wsas, WSA):
        rows = [wsa_to_feature_dict(wsas)]
    else:
        rows = [wsa_to_feature_dict(wsa) for wsa in wsas]
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)
