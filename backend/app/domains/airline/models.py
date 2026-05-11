from __future__ import annotations

from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import SMALLINT

from app.core.database import Base


class Airline(Base):
    __tablename__ = "airline"

    iata_code = Column(String(2), primary_key=True)
    airline_name = Column(String(128), nullable=False, unique=True)


class AircraftType(Base):
    __tablename__ = "aircraft_type"

    model = Column(String(32), primary_key=True)
    economy_seats = Column(SMALLINT(unsigned=True), nullable=False)
    first_seats = Column(SMALLINT(unsigned=True), nullable=False)
