"""
One-off clean-up for authorities stored more than once under different name
spellings. The ETL no longer creates them (see etl.load.merge_sources); this
merges the ones already in the database.

Usage:
    cd backend
    PYTHONPATH=. .venv/bin/python -m etl.dedupe_wsa            # dry run, prints the plan
    PYTHONPATH=. .venv/bin/python -m etl.dedupe_wsa --apply    # merge, in one transaction

Take a backup first (pg_dump): merging deletes the duplicate rows.
"""
import sys
from collections import defaultdict

from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from etl.load import PROVINCE_CENTROIDS, authority_key

_GAP_FIELDS = [
    "blue_drop_score", "green_drop_score", "nrw_percent", "maint_pct", "maint_expenditure", "asset_value",
    "num_water_supply_systems", "bdrr_score", "bdrr_risk_level", "cap_due_date", "summary",
]


def find_duplicate_groups(wsas: list[models.WSA]) -> list[list[models.WSA]]:
    groups: dict[tuple[str, str], list[models.WSA]] = defaultdict(list)
    for wsa in wsas:
        groups[authority_key(wsa.name, wsa.province)].append(wsa)
    return [g for g in groups.values() if len(g) > 1]


def _richness(wsa: models.WSA) -> tuple:
    # keep the row that already carries the most evidence: a Blue Drop score first, then a DWS label, then how many fields are filled
    filled = sum(1 for f in _GAP_FIELDS if getattr(wsa, f) is not None)
    return (wsa.blue_drop_score is not None, wsa.bdrr_risk_level is not None, filled, len(wsa.name))


def _is_centroid(wsa: models.WSA) -> bool:
    return PROVINCE_CENTROIDS.get(wsa.province) == (wsa.lat, wsa.lng) or (wsa.lat, wsa.lng) == (0.0, 0.0)


def merge_duplicate_wsas(db: Session, dry_run: bool = True) -> dict:
    groups = find_duplicate_groups(db.query(models.WSA).all())
    summary = {"groups": len(groups), "rows_removed": 0, "reports_moved": 0, "alerts_moved": 0, "history_dropped": 0, "plan": []}

    for group in groups:
        group.sort(key=_richness, reverse=True)
        keeper, extras = group[0], group[1:]
        summary["plan"].append((keeper.name, [e.name for e in extras]))
        for extra in extras:
            reports = db.query(models.CitizenReport).filter_by(wsa_id=extra.id)
            alerts = db.query(models.Alert).filter_by(wsa_id=extra.id)
            summary["reports_moved"] += reports.count()
            summary["alerts_moved"] += alerts.count()
            summary["history_dropped"] += db.query(models.RiskScoreHistory).filter_by(wsa_id=extra.id).count()
            summary["rows_removed"] += 1
            if dry_run:
                continue

            for field in _GAP_FIELDS:
                if getattr(keeper, field) is None and getattr(extra, field) is not None:
                    setattr(keeper, field, getattr(extra, field))
            # a CAP an admin recorded on the duplicate must not be lost
            if keeper.cap_status == models.CAPStatus.none and extra.cap_status != models.CAPStatus.none:
                keeper.cap_status = extra.cap_status
            if keeper.dws_cap_status == models.DWSCAPStatus.none and extra.dws_cap_status != models.DWSCAPStatus.none:
                keeper.dws_cap_status = extra.dws_cap_status
            if _is_centroid(keeper) and not _is_centroid(extra):
                keeper.lat, keeper.lng = extra.lat, extra.lng

            # citizen data follows the authority; the duplicate's score history is dropped with it because the keeper has its own
            reports.update({"wsa_id": keeper.id})
            alerts.update({"wsa_id": keeper.id})

    if not dry_run:
        db.flush()
        for _keeper_name, extra_names in summary["plan"]:
            for name in extra_names:
                row = db.query(models.WSA).filter_by(name=name).first()
                if row:
                    db.delete(row)
        db.flush()
    return summary


def main() -> None:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        summary = merge_duplicate_wsas(db, dry_run=not apply)
        print(f"{'APPLIED' if apply else 'DRY RUN'}: {summary['groups']} duplicate groups, {summary['rows_removed']} rows to remove, "
              f"{summary['reports_moved']} reports and {summary['alerts_moved']} alerts moved, {summary['history_dropped']} history rows dropped")
        for keeper, extras in summary["plan"][:15]:
            print(f"  keep {keeper!r}  <-  {extras}")
        if apply:
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
