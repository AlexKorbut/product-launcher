"""Shared helpers for worker processes."""
import logging

from app.db import SessionLocal
from app.models import Alert, AlertKind, WorkerLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def log(worker: str, message: str, level: str = "info", org_id: int | None = None) -> None:
    logging.getLogger(worker).log(
        logging.ERROR if level == "error" else logging.INFO, message
    )
    async with SessionLocal() as session:
        session.add(WorkerLog(worker=worker, level=level, message=message[:4000], org_id=org_id))
        await session.commit()


async def raise_alert(org_id: int, kind: AlertKind, message: str) -> None:
    """Create a dashboard alert, de-duplicating unread alerts of the same kind."""
    from sqlalchemy import select

    async with SessionLocal() as session:
        existing = await session.scalar(
            select(Alert).where(
                Alert.org_id == org_id, Alert.kind == kind, Alert.is_read.is_(False)
            )
        )
        if existing:
            return
        session.add(Alert(org_id=org_id, kind=kind, message=message[:1000]))
        await session.commit()
