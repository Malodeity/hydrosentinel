import pandas as pd
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import BDCertification, CAPStatus, DWSCAPStatus, NDPerformance, RiskLevel, WSA

# same centroids used to seed demo WSAs in main.py — reused here as a fallback
# for real WSAs whose source PDFs carry no GPS coordinates
PROVINCE_CENTROIDS: dict[str, tuple[float, float]] = {
    "Eastern Cape": (-32.0, 26.5),
    "Free State": (-28.6, 27.3),
    "Gauteng": (-26.2, 28.1),
    "KwaZulu-Natal": (-29.7, 30.7),
    "Limpopo": (-23.9, 29.5),
    "Mpumalanga": (-25.5, 30.9),
    "Northern Cape": (-29.0, 22.8),
    "North West": (-26.5, 25.6),
    "Western Cape": (-33.8, 19.9),
}


def merge_sources(
    blue_drop: pd.DataFrame,
    no_drop: pd.DataFrame,
    green_drop: pd.DataFrame,
    money: pd.DataFrame,
) -> pd.DataFrame:
    # this outer-joins all four sources on WSA name so partial data is never lost
    frames = [f for f in [blue_drop, no_drop, green_drop, money] if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["name", "blue_drop_score", "nrw_percent", "green_drop_score",
                                     "bd_certification", "nd_performance", "num_water_supply_systems",
                                     "maint_pct", "maint_expenditure", "asset_value"])
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="name", how="outer")

    # When multiple sources both carry a "province" column pandas suffixes them
    # (_x, _y). Coalesce them back into a single "province" column.
    province_cols = [c for c in merged.columns if c.startswith("province")]
    if len(province_cols) > 1:
        merged["province"] = merged[province_cols].bfill(axis=1).iloc[:, 0]
        merged.drop(columns=[c for c in province_cols if c != "province"], inplace=True)

    return merged


def upsert_wsa_rows(frame: pd.DataFrame, session: Session | None = None) -> int:
    # this writes one row per WSA, creating it when absent and updating fields when present
    inserted_or_updated = 0
    db: Session = session or SessionLocal()
    try:
        for row in frame.to_dict(orient="records"):
            wsa = db.query(WSA).filter(WSA.name == row["name"]).first()
            province = row.get("province")
            province = province if province and str(province) != "nan" else None
            if not wsa:
                lat, lng = PROVINCE_CENTROIDS.get(province, (0.0, 0.0))
                wsa = WSA(
                    name=row["name"],
                    province=province or "Unknown",
                    cap_status=CAPStatus.none,
                    dws_cap_status=DWSCAPStatus.none,
                    risk_level=RiskLevel.low,
                    lat=lat,
                    lng=lng,
                )
            else:
                if province and wsa.province == "Unknown":
                    wsa.province = province
                if (wsa.lat, wsa.lng) == (0.0, 0.0) and province in PROVINCE_CENTROIDS:
                    wsa.lat, wsa.lng = PROVINCE_CENTROIDS[province]

            # numeric scores — None stays None (not zeroed out) so missing data is visible
            wsa.blue_drop_score = _float_or_none(row.get("blue_drop_score"))
            wsa.nrw_percent = _float_or_none(row.get("nrw_percent"))
            wsa.green_drop_score = _float_or_none(row.get("green_drop_score"))
            wsa.maint_pct = _float_or_none(row.get("maint_pct"))
            wsa.maint_expenditure = _float_or_none(row.get("maint_expenditure"))
            wsa.asset_value = _float_or_none(row.get("asset_value"))
            wsa.num_water_supply_systems = _int_or_none(row.get("num_water_supply_systems"))

            # enum fields — keep existing value when source has no data for this row
            bd = row.get("bd_certification")
            if bd and str(bd) != "nan":
                wsa.bd_certification = BDCertification(bd)
            nd = row.get("nd_performance")
            if nd and str(nd) != "nan":
                wsa.nd_performance = NDPerformance(nd)

            db.add(wsa)
            inserted_or_updated += 1

        db.commit()
        return inserted_or_updated
    finally:
        if session is None:
            db.close()


def _float_or_none(value) -> float | None:
    try:
        return float(value) if value is not None and str(value).strip() not in ("", "nan") else None
    except (TypeError, ValueError):
        return None


def _int_or_none(value) -> int | None:
    try:
        return int(float(value)) if value is not None and str(value).strip() not in ("", "nan") else None
    except (TypeError, ValueError):
        return None
