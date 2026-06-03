from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey, ForeignKeyConstraint, Numeric, String
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class Ticket(Base):
    __tablename__ = "ticket"

    ticket_no = Column(String(32), primary_key=True)
    order_no = Column(String(32), ForeignKey("aptorder.order_no"), nullable=False)
    passenger_id = Column(String(32), ForeignKey("passenger.id_no"), nullable=False)
    instance_id = Column(String(32), nullable=False)
    cabin_class = Column(Enum("经济舱", "头等舱"), nullable=False)
    fare_type = Column(Enum("标准", "特价"), nullable=False, default="标准")
    actual_price = Column(Numeric(10, 2), nullable=False)
    fuel_infra_fee = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(
        Enum("有效", "已退", "已改签作废", "已使用"),
        nullable=False,
        default="有效",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["instance_id", "cabin_class", "fare_type"],
            ["cabin_price.instance_id", "cabin_price.cabin_class", "cabin_price.fare_type"],
        ),
    )


class RefundChange(Base):
    __tablename__ = "refund_change"

    refund_id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    ticket_no = Column(String(32), ForeignKey("ticket.ticket_no"), nullable=False)
    op_type = Column(Enum("退票", "改签"), nullable=False)
    fee = Column(Numeric(10, 2), nullable=False, default=0)
    new_ticket_no = Column(String(32), ForeignKey("ticket.ticket_no"), nullable=True)
    price_diff = Column(Numeric(10, 2), nullable=False, default=0)
    op_time = Column(DateTime, nullable=False)
