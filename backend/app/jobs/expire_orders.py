from __future__ import annotations

from app.core.logging import get_logger


logger = get_logger(__name__)


def expire_orders_job() -> None:
    logger.debug("超时订单扫描任务暂未实现")
