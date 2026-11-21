# Scheduled re-scoring (FR-10). A background task wakes up now and then and scores every authority whose latest score is older than
# RESCORE_INTERVAL_HOURS (0 turns it off). It uses the same scoring code as the "Score risk now" button (routes/risk.py record_score),
# so it also raises the same alerts. A history row with scored_by empty marks an automatic run.
#
# It is safe with several servers and with restarts: it only scores authorities that are actually due, and a database lock means
# only one server does the work at a time.

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import models
from app.database import SessionLocal
from app.routes.risk import record_score

log = logging.getLogger("hydrosentinel.scheduler")
_LOCK_KEY = 7310001  # any fixed number; every server asks for the same lock


# scores the authorities that are due and returns how many it scored. 0 when none are due, or when another server holds the lock
def rescore_due(model, interval_hours: float, db=None) -> int:
    own_session = db is None  # tests pass their own session
    db = db or SessionLocal()
    try:
        # a transaction-level lock: it is released by the commit below (or a rollback), and it cannot leak onto a pooled connection the way a
        # session-level lock can, because the session hands its connection back to the pool when it commits
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": _LOCK_KEY}):
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=interval_hours)
        scored = 0
        for wsa in db.query(models.WSA).all():
            latest = (
                db.query(models.RiskScoreHistory.scored_at)
                .filter(models.RiskScoreHistory.wsa_id == wsa.id)
                .order_by(models.RiskScoreHistory.scored_at.desc())
                .first()
            )
            if latest is not None and latest[0] >= cutoff:
                continue
            record_score(wsa, model, db, None)
            scored += 1
        db.commit()
        return scored
    except Exception:
        db.rollback()
        log.exception("scheduled re-scoring failed")
        return 0
    finally:
        if own_session:
            db.close()


# started from the app's lifespan. checks at least hourly, or more often when the interval is short (a short interval is for demonstrations)
async def run_forever(app, interval_hours: float) -> None:
    pause = min(3600.0, max(30.0, interval_hours * 3600 / 4))
    while True:
        count = await asyncio.to_thread(rescore_due, getattr(app.state, "risk_model", None), interval_hours)
        if count:
            log.info("scheduled re-scoring scored %s authorities", count)
        await asyncio.sleep(pause)
