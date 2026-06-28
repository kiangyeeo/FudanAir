from __future__ import annotations

from datetime import datetime

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.domains.flight.service import FlightService


logger = get_logger(__name__)


def sync_flight_status_job() -> None:
    with SessionLocal() as db:
        departed_count, arrived_count = FlightService(db).sync_time_statuses(datetime.now())
    if departed_count or arrived_count:
        logger.info(
            "航班实例状态已自动流转: 已起飞=%s, 已到达=%s",
            departed_count,
            arrived_count,
        )
