"""
A real bug hit while building the BDRR training evaluation: calling
train_test_split twice with the same random_state — once on string labels,
once on int-mapped labels — silently produces two DIFFERENT splits, because
sklearn orders stratification groups by np.unique() of the stratify array,
which sorts differently for strings ("high","low","medium") vs ints
(0,1,2). Comparing a model evaluated on one split against a heuristic
evaluated on the other looked like a real result (96.6% vs 31% accuracy)
but was comparing mismatched rows. The fix: split once, with all needed
label representations passed to the same train_test_split call.
"""
import pandas as pd
from sklearn.model_selection import train_test_split

RISK_TO_TARGET = {"low": 0, "medium": 1, "high": 2}


def test_splitting_string_and_int_labels_separately_gives_different_splits():
    # documents the actual bug — two separate calls with identical
    # random_state do NOT agree when the stratify dtype differs
    labels = pd.Series(["low"] * 20 + ["medium"] * 7 + ["high"] * 3)
    x = pd.DataFrame({"f": range(len(labels))})

    _, x_test_a, _, _ = train_test_split(x, labels, test_size=0.2, random_state=42, stratify=labels)
    mapped = labels.map(RISK_TO_TARGET)
    _, x_test_b, _, _ = train_test_split(x, mapped, test_size=0.2, random_state=42, stratify=mapped)

    assert list(x_test_a.index) != list(x_test_b.index)


def test_single_split_call_keeps_multiple_label_representations_aligned():
    labels = pd.Series(["low"] * 20 + ["medium"] * 7 + ["high"] * 3)
    mapped = labels.map(RISK_TO_TARGET)
    x = pd.DataFrame({"f": range(len(labels))})

    x_train, x_test, y_train, y_test, _, y_test_labels = train_test_split(
        x, mapped, labels, test_size=0.2, random_state=42, stratify=mapped,
    )

    assert list(x_test.index) == list(y_test_labels.index)
    for target_value, label in zip(y_test, y_test_labels):
        assert RISK_TO_TARGET[label] == target_value
