import pandas as pd
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import BDCertification, CAPStatus, DWSCAPStatus, NDPerformance, RiskLevel, WSA
from etl.name_matching import METRO_ALIASES, normalize_name

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


def authority_key(name: str, province: str | None) -> tuple[str, str]:
    """
    One key per real authority. Sources spell names differently ("Alfred Nzo DM"
    vs "Alfred Nzo District Municipality", "Cape Town" vs "City of Cape Town MM"),
    so names are compared after suffix stripping and metro aliasing. Province is
    part of the key because different provinces have same-named authorities.
    """
    norm = normalize_name(str(name))
    for primary, aliases in METRO_ALIASES.items():
        if norm == primary or norm in {normalize_name(a) for a in aliases}:
            norm = primary
            break
    return (str(province) if province and str(province) != "nan" else "", norm)


def _canonicalise_names(frames: list[pd.DataFrame]) -> list[pd.DataFrame]:
    # the first source to mention an authority (Blue Drop comes first) decides
    # the display name; later spellings are renamed to it so the outer join
    # below yields one row per authority instead of one per spelling
    canonical: dict[tuple[str, str], str] = {}
    used_names: set[str] = set()
    by_norm: dict[str, list[tuple[str, str]]] = {}
    out = []
    for frame in frames:
        frame = frame.copy()
        if "province" in frame.columns:
            keys = [authority_key(n, p) for n, p in zip(frame["name"], frame["province"])]
        else:
            # a source with no province can only be matched when the name is unambiguous
            keys = []
            for n in frame["name"]:
                norm = authority_key(n, None)[1]
                candidates = by_norm.get(norm, [])
                keys.append(candidates[0] if len(candidates) == 1 else authority_key(n, None))
        new_names = []
        for (key, original) in zip(keys, frame["name"]):
            if key not in canonical:
                # the same display name in two provinces stays distinct, since the join below is on name alone
                display = original if original not in used_names else f"{original} ({key[0] or 'unknown province'})"
                canonical[key] = display
                used_names.add(display)
                by_norm.setdefault(key[1], []).append(key)
            new_names.append(canonical[key])
        frame["name"] = new_names
        # two spellings of one authority inside a single source collapse to one row, keeping the first value found
        out.append(frame.groupby("name", as_index=False, sort=False).first())
    return out


def merge_sources(
    blue_drop: pd.DataFrame,
    no_drop: pd.DataFrame,
    green_drop: pd.DataFrame,
    money: pd.DataFrame,
    bdrr: pd.DataFrame | None = None,
) -> pd.DataFrame:
    # this outer-joins all sources on WSA name so partial data is never lost
    frames = [f for f in [blue_drop, no_drop, green_drop, money, bdrr] if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=["name", "blue_drop_score", "nrw_percent", "green_drop_score",
                                     "bd_certification", "nd_performance", "num_water_supply_systems",
                                     "maint_pct", "maint_expenditure", "asset_value",
                                     "bdrr_score_2023", "bdrr_risk_level"])
    frames = _canonicalise_names(frames)
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
        # match on the authority key, not the exact string, so a different spelling updates the existing row
        existing_by_key = {authority_key(w.name, w.province): w for w in db.query(WSA).all()}
        for row in frame.to_dict(orient="records"):
            province = row.get("province")
            province = province if province and str(province) != "nan" else None
            wsa = db.query(WSA).filter(WSA.name == row["name"]).first() or existing_by_key.get(authority_key(row["name"], province))
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
            wsa.bdrr_score = _float_or_none(row.get("bdrr_score_2023"))

            # enum fields — keep existing value when source has no data for this row
            bd = row.get("bd_certification")
            if bd and str(bd) != "nan":
                wsa.bd_certification = BDCertification(bd)
            nd = row.get("nd_performance")
            if nd and str(nd) != "nan":
                wsa.nd_performance = NDPerformance(nd)
            bdrr_risk = row.get("bdrr_risk_level")
            if bdrr_risk and str(bdrr_risk) != "nan":
                wsa.bdrr_risk_level = RiskLevel(bdrr_risk)

            db.add(wsa)
            existing_by_key[authority_key(wsa.name, wsa.province)] = wsa
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
