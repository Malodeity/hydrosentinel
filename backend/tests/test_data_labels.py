"""
maint_pct is maintenance as a share of total operating expenditure (the
Treasury API exposes no usable asset value). It must be labelled that way,
and a municipality with no maintenance figure must be skipped, not stored
as 0.00% ("spends nothing").
"""
from app import models
from app.routes.ai import _average_or_unavailable, build_wsa_prompt
from etl.municipal_money import _build_finance_rows


def test_prompt_labels_maintenance_as_share_of_operating_expenditure():
    wsa = models.WSA(name="P", province="Gauteng", maint_pct=8.75, lat=0, lng=0,
                     cap_status=models.CAPStatus.none, dws_cap_status=models.DWSCAPStatus.none,
                     bd_certification=models.BDCertification.non_certified, nd_performance=models.NDPerformance.average,
                     risk_level=models.RiskLevel.low)

    prompt = build_wsa_prompt(wsa)

    assert "operating expenditure" in prompt and "8.75" in prompt
    assert "asset value" not in prompt.lower()
    assert "8% benchmark" not in prompt


def test_average_is_unavailable_when_there_is_no_data():
    assert _average_or_unavailable([]) == "not available (no data)"
    assert _average_or_unavailable([10.0, 20.0]) == 15.0


def test_municipality_without_maintenance_data_is_skipped_not_zeroed():
    rows = _build_finance_rows(
        labels={"A": "Has data", "B": "No maintenance data", "C": "Reports zero"},
        maint={"A": 50.0, "C": 0.0},
        opex={"A": 1000.0, "B": 1000.0, "C": 1000.0},
    )

    by_label = {r["demarcation_label"]: r for r in rows}
    assert "No maintenance data" not in by_label
    assert by_label["Has data"]["maint_pct"] == 5.0
    assert by_label["Reports zero"]["maint_pct"] == 0.0
