import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from ai.features import FEATURE_COLUMNS

RISK_TO_TARGET = {"low": 0, "medium": 1, "high": 2}


def train_model_from_dataframe(frame: pd.DataFrame) -> XGBClassifier:
    missing_columns = set(FEATURE_COLUMNS + ["risk_level"]) - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Training data is missing columns: {sorted(missing_columns)}")

    x = frame[FEATURE_COLUMNS]
    y = frame["risk_level"].map(RISK_TO_TARGET)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        n_estimators=150,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    print(classification_report(y_test, predictions))
    return model


def persist_model(model: XGBClassifier, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python ai/train.py <training_csv_path> [output_model_path]")

    training_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("ai/model.pkl")

    frame = pd.read_csv(training_path)
    model = train_model_from_dataframe(frame)
    saved_path = persist_model(model, output_path)
    print(f"Model saved to {saved_path}")


if __name__ == "__main__":
    main()
