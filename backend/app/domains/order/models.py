from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class AptOrder(Base):
    __tablename__ = "aptorder"

    order_no = Column(String(32), primary_key=True)
    user_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("user.user_id"),
        nullable=False,
    )
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(
        Enum("待支付", "已支付", "已取消", "已完成", "部分退款", "已完成退款"),
        nullable=False,
        default="待支付",
    )
    created_at = Column(DateTime, nullable=False)
