"""
The DWS reports spell the same authority differently ("Alfred Nzo DM" vs
"Alfred Nzo District Municipality"). Joining them on the exact name string
produced two WSA rows for one authority: 116 of 284 rows were duplicates, the
duplicates mostly had no Blue Drop score (so they were scored by the weak
fallback) and the dashboard totals were overstated.
"""
import pandas as pd

from app import models
from etl.dedupe_wsa import find_duplicate_groups, merge_duplicate_wsas
from etl.load import merge_sources

EMPTY = pd.DataFrame()


def test_merge_sources_joins_the_same_authority_spelled_two_ways():
    blue = pd.DataFrame([{"name": "Alfred Nzo District Municipality", "province": "Eastern Cape", "blue_drop_score": 40.0}])
    bdrr = pd.DataFrame([{"name": "Alfred Nzo DM", "province": "Eastern Cape", "bdrr_score_2023": 55.0, "bdrr_risk_level": "medium"}])

    merged = merge_sources(blue, EMPTY, EMPTY, EMPTY, bdrr)

    assert len(merged) == 1
    row = merged.iloc[0]
    assert row["name"] == "Alfred Nzo District Municipality"
    assert row["blue_drop_score"] == 40.0 and row["bdrr_risk_level"] == "medium"


def test_merge_sources_keeps_same_named_authorities_in_different_provinces_apart():
    blue = pd.DataFrame([
        {"name": "Emalahleni LM", "province": "Mpumalanga", "blue_drop_score": 60.0},
        {"name": "Emalahleni LM", "province": "Eastern Cape", "blue_drop_score": 30.0},
    ])
    bdrr = pd.DataFrame([{"name": "Emalahleni Local Municipality", "province": "Eastern Cape", "bdrr_score_2023": 70.0, "bdrr_risk_level": "high"}])

    merged = merge_sources(blue, EMPTY, EMPTY, EMPTY, bdrr)

    assert len(merged) == 2
    eastern = merged[merged["province"] == "Eastern Cape"].iloc[0]
    assert eastern["blue_drop_score"] == 30.0 and eastern["bdrr_risk_level"] == "high"


def test_merge_sources_joins_metro_aliases():
    blue = pd.DataFrame([{"name": "City of Cape Town MM", "province": "Western Cape", "blue_drop_score": 90.0}])
    no_drop = pd.DataFrame([{"name": "Cape Town", "province": "Western Cape", "nd_performance": "good"}])

    merged = merge_sources(blue, no_drop, EMPTY, EMPTY, None)

    assert len(merged) == 1
    assert merged.iloc[0]["nd_performance"] == "good"


def _wsa(db, name, province="Gauteng", **fields):
    wsa = models.WSA(name=name, province=province, lat=-26.0, lng=28.0, **fields)
    db.add(wsa)
    db.flush()
    return wsa


def test_find_duplicate_groups_uses_province_and_normalised_name(db):
    a = _wsa(db, "Zzdupville DM")
    b = _wsa(db, "Zzdupville District Municipality")
    other_province = _wsa(db, "Zzdupville Local Municipality", province="Limpopo")

    groups = find_duplicate_groups([a, b, other_province])

    assert len(groups) == 1
    assert {w.id for w in groups[0]} == {a.id, b.id}


def test_merge_keeps_the_scored_row_moves_reports_and_fills_gaps(db):
    scored = _wsa(db, "Zzmerge District Municipality", blue_drop_score=55.0, bdrr_risk_level=models.RiskLevel.medium)
    bare = _wsa(db, "Zzmerge DM", cap_status=models.CAPStatus.submitted, green_drop_score=41.0)
    report = models.CitizenReport(wsa_id=bare.id, issue_type=models.IssueType.leak, description="leak on main road",
                                  reference_code="HS-ZZMERGE1", case_status="open", lat=-26.0, lng=28.0)
    db.add(report)
    db.flush()

    merge_duplicate_wsas(db, dry_run=False)
    db.expire_all()

    survivors = db.query(models.WSA).filter(models.WSA.name.like("Zzmerge%")).all()
    assert len(survivors) == 1
    keeper = survivors[0]
    assert keeper.name == "Zzmerge District Municipality" and keeper.blue_drop_score == 55.0
    assert keeper.green_drop_score == 41.0
    assert keeper.cap_status == models.CAPStatus.submitted
    assert db.query(models.CitizenReport).filter_by(reference_code="HS-ZZMERGE1").one().wsa_id == keeper.id


def test_dry_run_changes_nothing(db):
    _wsa(db, "Zzdry LM", blue_drop_score=10.0)
    _wsa(db, "Zzdry Local Municipality")

    summary = merge_duplicate_wsas(db, dry_run=True)
    db.expire_all()

    assert db.query(models.WSA).filter(models.WSA.name.like("Zzdry%")).count() == 2
    assert summary["groups"] >= 1


def test_upsert_updates_the_existing_row_when_the_source_spells_the_name_differently(db):
    from etl.load import upsert_wsa_rows
    existing = _wsa(db, "Zzupsert LM", blue_drop_score=10.0)

    upsert_wsa_rows(pd.DataFrame([{"name": "Zzupsert Local Municipality", "province": "Gauteng", "blue_drop_score": 77.0}]), session=db)
    db.expire_all()

    rows = db.query(models.WSA).filter(models.WSA.name.like("Zzupsert%")).all()
    assert len(rows) == 1
    assert rows[0].id == existing.id and rows[0].blue_drop_score == 77.0
