from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from app.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.domains.flight.service import FlightService


logger = get_logger(__name__)


def generate_instances_daily() -> None:
    target_date = date.today() + timedelta(days=settings.INSTANCE_AHEAD_DAYS)
    weekday = target_date.isoweekday()
    with SessionLocal() as db:
        flight_numbers = db.execute(
            text(
                """
                SELECT DISTINCT flight_no
                FROM flight_weekday
                WHERE weekday = :weekday
                ORDER BY flight_no
                """
            ),
            {"weekday": weekday},
        ).scalars().all()
        for flight_no in flight_numbers:
            FlightService(db).create_instance(str(flight_no), target_date)
    logger.info("已生成 %s 的航班实例,航班数=%s", target_date, len(flight_numbers))
