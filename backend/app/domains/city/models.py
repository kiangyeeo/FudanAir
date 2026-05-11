from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Numeric, String

from app.core.database import Base


class City(Base):
    __tablename__ = "city"

    city_name = Column(String(32), primary_key=True)


class Airport(Base):
    __tablename__ = "airport"

    iata_code = Column(String(3), primary_key=True)
    airport_name = Column(String(128), nullable=False)
    city_name = Column(
        String(32),
        ForeignKey("city.city_name", onupdate="CASCADE"),
        nullable=False,
    )


class CityNearApt(Base):
    __tablename__ = "city_near_apt"

    city_name = Column(
        String(32),
        ForeignKey("city.city_name", ondelete="CASCADE"),
        primary_key=True,
    )
    iata_code = Column(
        String(3),
        ForeignKey("airport.iata_code", ondelete="CASCADE"),
        primary_key=True,
    )
    distance = Column(Numeric(6, 2), nullable=False)
