from __future__ import annotations

from sqlalchemy import Column, Date, String

from app.core.database import Base


class Passenger(Base):
    __tablename__ = "passenger"

    id_no = Column(String(32), primary_key=True)
    real_name = Column(String(64), nullable=False)
    birth_date = Column(Date, nullable=False)
