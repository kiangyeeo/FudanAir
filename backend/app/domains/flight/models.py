from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Numeric, String, Time
from sqlalchemy.dialects.mysql import SMALLINT, TINYINT

from app.core.database import Base


class Flight(Base):
    __tablename__ = "flight"

    flight_no = Column(String(8), primary_key=True)
    scheduled_departure = Column(Time, nullable=False)
    scheduled_arrival = Column(Time, nullable=False)
    fuel_infra_fee = Column(Numeric(10, 2), nullable=False, default=0)
    dep_airport_code = Column(
        String(3),
        ForeignKey("airport.iata_code"),
        nullable=False,
    )
    dep_terminal = Column(String(8), nullable=True)
    arr_airport_code = Column(
        String(3),
        ForeignKey("airport.iata_code"),
        nullable=False,
    )
    arr_terminal = Column(String(8), nullable=True)
    airline_code = Column(
        String(2),
        ForeignKey("airline.iata_code"),
        nullable=False,
    )
    aircraft_model = Column(
        String(32),
        ForeignKey("aircraft_type.model"),
        nullable=False,
    )


class FlightWeekday(Base):
    __tablename__ = "flight_weekday"

    flight_no = Column(
        String(8),
        ForeignKey("flight.flight_no", ondelete="CASCADE"),
        primary_key=True,
    )
    weekday = Column(TINYINT, primary_key=True)


class FlightStopover(Base):
    __tablename__ = "flight_stopover"

    flight_no = Column(
        String(8),
        ForeignKey("flight.flight_no", ondelete="CASCADE"),
        primary_key=True,
    )
    stop_order = Column(TINYINT(unsigned=True), primary_key=True)
    airport_code = Column(
        String(3),
        ForeignKey("airport.iata_code"),
        nullable=False,
    )


class FlightInstance(Base):
    __tablename__ = "flight_instance"

    instance_id = Column(String(32), primary_key=True)
    flight_no = Column(
        String(8),
        ForeignKey("flight.flight_no"),
        nullable=False,
    )
    flight_date = Column(Date, nullable=False)
    scheduled_departure = Column(Time, nullable=False)
    scheduled_arrival = Column(Time, nullable=False)
    fuel_infra_fee = Column(Numeric(10, 2), nullable=False, default=0)
    adjusted_at = Column(DateTime, nullable=True)
    scheduled_departure_adjusted_at = Column(DateTime, nullable=True)
    scheduled_arrival_adjusted_at = Column(DateTime, nullable=True)
    dep_airport_adjusted_at = Column(DateTime, nullable=True)
    arr_airport_adjusted_at = Column(DateTime, nullable=True)
    economy_left = Column(SMALLINT(unsigned=True), nullable=False)
    first_left = Column(SMALLINT(unsigned=True), nullable=False)
    status = Column(
        Enum("计划", "可订", "已起飞", "已到达", "已取消"),
        nullable=False,
        default="计划",
    )


class CabinPrice(Base):
    __tablename__ = "cabin_price"

    instance_id = Column(
        String(32),
        ForeignKey("flight_instance.instance_id", ondelete="CASCADE"),
        primary_key=True,
    )
    cabin_class = Column(Enum("经济舱", "头等舱"), primary_key=True)
    fare_type = Column(Enum("标准", "特价"), primary_key=True, default="标准")
    price = Column(Numeric(10, 2), nullable=False)
    available_seats = Column(SMALLINT(unsigned=True), nullable=False, default=0)
