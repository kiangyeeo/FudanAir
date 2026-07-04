from __future__ import annotations

from datetime import datetime, timedelta

from app.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.domains.order.repository import OrderRepository
from app.workflows.booking.service import BookingService


logger = get_logger(__name__)


def expire_orders_job() -> None:
    expire_before = datetime.now() - timedelta(minutes=settings.ORDER_EXPIRE_MINUTES)
    with SessionLocal() as db:
        order_nos = OrderRepository(db).list_expired_pending_order_nos(expire_before)
        for order_no in order_nos:
            try:
                if BookingService(db).expire_order(order_no):
                    logger.info("Order %s expired, canceled, and stock was restored", order_no)
            except Exception as exc:
                logger.exception("Failed to process expired order %s: %s", order_no, exc)
