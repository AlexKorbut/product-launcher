"""Shared helpers for worker processes."""
import logging

from app.db import SessionLocal
from app.models import WorkerLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


async def log(worker: str, message: str, level: str = "info") -> None:
    logging.getLogger(worker).log(
        logging.ERROR if level == "error" else logging.INFO, message
    )
    async with SessionLocal() as session:
        session.add(WorkerLog(worker=worker, level=level, message=message[:4000]))
        await session.commit()
