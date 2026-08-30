"""
Treasury's Municipal Money API names municipalities differently than the DWS
report names already on WSA rows (district labels drop the "DM" suffix,
metros diverge structurally — "Cape Town" vs "City of Cape Town"). A
matching regression here silently drops maint_pct for real WSAs, or worse,
attaches finance data to the wrong municipality.
"""
import pandas as pd

from etl.municipal_money import _build_finance_rows, _normalize, load_municipal_money, match_to_wsa_names


def test_normalize_strips_common_suffixes():
    assert _normalize("Alfred Nzo DM") == "alfred nzo"
    assert _normalize("Alfred Nzo District Municipality") == "alfred nzo"
    assert _normalize("Buffalo City LM") == "buffalo city"
    assert _normalize("Buffalo City Local Municipality") == "buffalo city"
    assert _normalize("City of Ekurhuleni") == "city of ekurhuleni"


def test_normalize_is_case_and_whitespace_insensitive():
    assert _normalize("  Chris Hani   DM ") == _normalize("chris hani dm")


def test_match_to_wsa_names_matches_district_label_without_dm_suffix():
    finance = pd.DataFrame([
        {"demarcation_code": "DC13", "demarcation_label": "Chris Hani", "maint_pct": 5.2, "maint_expenditure": 1_000_000.0},
    ])
    known_names = ["Chris Hani DM", "Some Other WSA"]

    result = match_to_wsa_names(finance, known_names)

    assert len(result) == 1
    assert result.iloc[0]["name"] == "Chris Hani DM"
    assert result.iloc[0]["maint_pct"] == 5.2


def test_match_to_wsa_names_resolves_metro_alias():
    finance = pd.DataFrame([
        {"demarcation_code": "CPT", "demarcation_label": "Cape Town", "maint_pct": 4.8, "maint_expenditure": 2_000_000.0},
    ])
    known_names = ["City of Cape Town"]

    result = match_to_wsa_names(finance, known_names)

    assert len(result) == 1
    assert result.iloc[0]["name"] == "City of Cape Town"


def test_match_to_wsa_names_expands_to_multiple_known_name_variants():
    # our own WSA table already has duplicate rows for the same real
    # municipality under different naming conventions (a pre-existing
    # dedup gap in other parsers) — every variant should still get matched
    finance = pd.DataFrame([
        {"demarcation_code": "DC12", "demarcation_label": "Amathole", "maint_pct": 6.1, "maint_expenditure": 500_000.0},
    ])
    known_names = ["Amathole DM", "Amathole District Municipality", "Unrelated WSA"]

    result = match_to_wsa_names(finance, known_names)

    assert set(result["name"]) == {"Amathole DM", "Amathole District Municipality"}


def test_match_to_wsa_names_skips_unmatched_municipality():
    finance = pd.DataFrame([
        {"demarcation_code": "XYZ", "demarcation_label": "Nonexistent Place", "maint_pct": 3.0, "maint_expenditure": 100.0},
    ])
    result = match_to_wsa_names(finance, ["Some WSA"])
    assert result.empty


def test_match_to_wsa_names_handles_empty_finance_frame():
    result = match_to_wsa_names(pd.DataFrame(columns=["demarcation_code", "demarcation_label", "maint_pct", "maint_expenditure"]), ["Some WSA"])
    assert result.empty


def test_build_finance_rows_discards_negative_ratio_from_accounting_reversal():
    # a real case hit in production: Masilonyana LM had a negative audited
    # repairs & maintenance figure, producing maint_pct = -0.56 — that broke
    # the DB's 0-100 check constraint and must never reach the output
    labels = {"MAS": "Masilonyana"}
    maint = {"MAS": -381_865.0}
    opex = {"MAS": 68_000_000.0}

    rows = _build_finance_rows(labels, maint, opex)

    assert rows == []


def test_build_finance_rows_keeps_valid_ratio():
    labels = {"BUF": "Buffalo City"}
    maint = {"BUF": 445_308_256.0}
    opex = {"BUF": 9_108_938_273.0}

    rows = _build_finance_rows(labels, maint, opex)

    assert len(rows) == 1
    assert rows[0]["demarcation_label"] == "Buffalo City"
    assert 4.0 < rows[0]["maint_pct"] < 5.0


def test_build_finance_rows_skips_municipality_with_no_expenditure_data():
    rows = _build_finance_rows({"XYZ": "Nowhere"}, {"XYZ": 1000.0}, {})
    assert rows == []


def test_load_municipal_money_missing_file_returns_empty_frame():
    result = load_municipal_money("/nonexistent/path.csv")
    assert result.empty
    assert list(result.columns) == ["name", "maint_pct", "maint_expenditure", "asset_value"]


def test_load_municipal_money_computes_pct_from_expenditure_and_assets(tmp_path):
    csv_path = tmp_path / "municipal_money.csv"
    csv_path.write_text("name,maint_expenditure,asset_value\nTest WSA,80000,1000000\n")

    result = load_municipal_money(csv_path)

    assert len(result) == 1
    assert result.iloc[0]["maint_pct"] == 8.0
