"""
Trains XGBoost on the 144 WSAs that carry a DWS-audited BDRR ground-truth
risk label (see etl/parse_bdrr.py), then evaluates it against the existing
heuristic on the same held-out split — so "should this model replace the
heuristic" is answered by a number, not a guess.

Usage:
    cd backend
    PYTHONPATH=. .venv/bin/python ai/train_from_bdrr.py            # evaluate only
    PYTHONPATH=. .venv/bin/python ai/train_from_bdrr.py --deploy   # evaluate, then
                                                                    # retrain on all
                                                                    # labeled rows and
                                                                    # write ai/model.pkl

Evaluation is a single 80/20 holdout (used for the direct heuristic
comparison) plus 5-fold stratified cross-validation, since 144 rows makes a
single split's accuracy noisy on its own — the CV mean/std is the number to
trust more.
"""
import sys

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from ai.features import FEATURE_COLUMNS, wsa_to_feature_dict
from ai.predict import _heuristic_probability, _probability_to_risk
from ai.train import RISK_TO_TARGET, build_classifier, persist_model
from app.database import SessionLocal
from app.models import WSA


def load_labeled_wsas() -> list[WSA]:
    db = SessionLocal()
    try:
        return db.query(WSA).filter(WSA.bdrr_risk_level.isnot(None)).all()
    finally:
        db.close()


def main() -> None:
    wsas = load_labeled_wsas()
    if len(wsas) < 20:
        print(f"Only {len(wsas)} labeled WSAs — too few to train/evaluate meaningfully. Aborting.")
        sys.exit(1)

    frame = pd.DataFrame([wsa_to_feature_dict(w) for w in wsas], columns=FEATURE_COLUMNS)
    frame["risk_level"] = [w.bdrr_risk_level.value for w in wsas]

    print(f"Training set: {len(frame)} labeled WSAs")
    print(frame["risk_level"].value_counts().to_string())
    print()

    # a SINGLE split, done once, used for training and both evaluations —
    # calling train_test_split twice with the same random_state does NOT
    # reproduce the same split when the stratify column's dtype differs
    # (string vs int-mapped labels sort into a different class order), so
    # this must not be split separately for the model vs the heuristic
    x = frame[FEATURE_COLUMNS]
    y_labels = frame["risk_level"]
    y_target = y_labels.map(RISK_TO_TARGET)

    x_train, x_test, y_train, y_test, _y_train_labels, y_test_labels = train_test_split(
        x, y_target, y_labels, test_size=0.2, random_state=42, stratify=y_target,
    )
    test_wsas = [wsas[i] for i in x_test.index]

    model = build_classifier()
    model.fit(x_train, y_train)

    target_to_risk = {v: k for k, v in RISK_TO_TARGET.items()}
    xgb_preds = [target_to_risk[p] for p in model.predict(x_test)]
    heuristic_preds = [_probability_to_risk(_heuristic_probability(w)).value for w in test_wsas]

    print("=== XGBoost ===")
    print(classification_report(y_test_labels, xgb_preds, zero_division=0))

    print("=== Heuristic (current production fallback) ===")
    print(classification_report(y_test_labels, heuristic_preds, zero_division=0))

    print("=== Head-to-head on held-out set ===")
    print(f"XGBoost accuracy:   {accuracy_score(y_test_labels, xgb_preds):.1%}")
    print(f"Heuristic accuracy: {accuracy_score(y_test_labels, heuristic_preds):.1%}")
    print(f"Test set size: {len(y_test_labels)} (train set: {len(y_train)})")
    print()

    print("=== 5-fold stratified cross-validation (more robust than one 80/20 split) ===")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(build_classifier(), x, y_target, cv=cv, scoring="accuracy")
    print(f"Fold accuracies: {[round(s, 3) for s in cv_scores]}")
    print(f"Mean: {cv_scores.mean():.1%}  Std: {cv_scores.std():.1%}")

    if "--deploy" in sys.argv:
        print()
        print("=== Deploying: retraining on all labeled rows ===")
        final_model = build_classifier()
        final_model.fit(x, y_target)
        saved_path = persist_model(final_model, "ai/model.pkl")
        print(f"Model saved to {saved_path}")


if __name__ == "__main__":
    main()
