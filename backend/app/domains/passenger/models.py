from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class Passenger(Base):
    __tablename__ = "passenger"

    id_no = Column(String(32), primary_key=True)
    real_name = Column(String(64), nullable=False)
    birth_date = Column(Date, nullable=False)


class UserPassenger(Base):
    __tablename__ = "user_passenger"

    user_id = Column(BIGINT(unsigned=True), ForeignKey("user.user_id"), primary_key=True)
    id_no = Column(String(32), ForeignKey("passenger.id_no"), primary_key=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
