"""
Real WSAs from ETL sources have no GPS coordinates in the source PDFs, so
upsert_wsa_rows must fall back to a province centroid instead of leaving
lat/lng at 0.0 (which renders as a marker in the Gulf of Guinea, off Africa).
"""
import pandas as pd

from etl.load import PROVINCE_CENTROIDS, upsert_wsa_rows


def test_province_centroids_cover_all_nine_provinces():
    expected = {
        "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
        "Mpumalanga", "Northern Cape", "North West", "Western Cape",
    }
    assert set(PROVINCE_CENTROIDS.keys()) == expected


def test_new_wsa_gets_province_centroid_when_source_has_no_coords(db):
    frame = pd.DataFrame([{"name": "Test No-Coord WSA", "province": "Gauteng", "blue_drop_score": 80.0}])
    upsert_wsa_rows(frame, session=db)

    from app import models
    wsa = db.query(models.WSA).filter(models.WSA.name == "Test No-Coord WSA").first()
    assert wsa is not None
    assert (wsa.lat, wsa.lng) == PROVINCE_CENTROIDS["Gauteng"]


def test_existing_nonzero_coords_are_not_overwritten(db):
    from app import models

    wsa = models.WSA(name="Has Real Coords WSA", province="Limpopo", lat=-23.5, lng=29.0, cap_status="none", risk_level="low")
    db.add(wsa)
    db.flush()

    frame = pd.DataFrame([{"name": "Has Real Coords WSA", "province": "Limpopo", "blue_drop_score": 70.0}])
    upsert_wsa_rows(frame, session=db)

    db.refresh(wsa)
    assert (wsa.lat, wsa.lng) == (-23.5, 29.0)


def test_unknown_province_falls_back_to_zero_not_crash(db):
    frame = pd.DataFrame([{"name": "Mystery Province WSA", "province": "Nowhereland", "blue_drop_score": 50.0}])
    upsert_wsa_rows(frame, session=db)

    from app import models
    wsa = db.query(models.WSA).filter(models.WSA.name == "Mystery Province WSA").first()
    assert wsa is not None
    assert (wsa.lat, wsa.lng) == (0.0, 0.0)
