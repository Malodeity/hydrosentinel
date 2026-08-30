"""
BDRR is our only source of ground-truth risk labels (independent of the
heuristic/XGBoost pipeline it's meant to train against). A parsing
regression here silently poisons the training set — the row-extraction
logic must keep matching real report rows and rejecting noise rows
(totals, legend text, incomplete rows).
"""
from etl.parse_bdrr import _classify_bdrr, _extract_name_and_scores


def test_classify_bdrr_matches_report_barometer_thresholds():
    assert _classify_bdrr(17.8) == "low"
    assert _classify_bdrr(49.9) == "low"
    assert _classify_bdrr(50.0) == "medium"
    assert _classify_bdrr(69.9) == "medium"
    assert _classify_bdrr(70.0) == "high"
    assert _classify_bdrr(94.6) == "high"
    assert _classify_bdrr(100.0) == "high"


def test_extract_name_and_scores_parses_real_report_row():
    row = ["", "Alfred Nzo DM", "", "7", None, None, "", None, None, "47.1%", None, None, "35.6%", None, None, "", "↑"]
    result = _extract_name_and_scores(row)
    assert result == ("Alfred Nzo DM", 47.1, 35.6)


def test_extract_name_and_scores_handles_extra_leading_numeric_column():
    # Gauteng-style rows carry an extra "# WBs/WSPs" numeric column before the percentages
    row = ["", "City of Ekurhuleni", "", "1", None, None, "1", None, None, "33.3%", None, None, "29.2%", None, None, "", "↑"]
    result = _extract_name_and_scores(row)
    assert result == ("City of Ekurhuleni", 33.3, 29.2)


def test_extract_name_and_scores_rejects_totals_row():
    row = ["", "Totals & %BDRR/BDRR\nmax", "", "", "154", "", "", "18", "", "", "51.6%", "", "", "46.1%"]
    assert _extract_name_and_scores(row) is None


def test_extract_name_and_scores_rejects_row_with_one_percent():
    row = ["", "", "", "28%", None, None, None, "", None, None]
    assert _extract_name_and_scores(row) is None


def test_extract_name_and_scores_rejects_empty_row():
    assert _extract_name_and_scores([None, None, "", None]) is None
