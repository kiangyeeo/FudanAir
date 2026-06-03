from __future__ import annotations

import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.domains.airline.models import AircraftType, Airline
from app.domains.city.models import Airport, City
from app.domains.flight.models import Flight, FlightInstance
from app.domains.flight.service import FlightService


def test_list_flights_filters_by_flight_no_prefix() -> None:
    db = _make_db()
    try:
        _seed_flight(db, "MU1001")
        _seed_flight(db, "MU2002")
        _seed_flight(db, "CA1001")
        _seed_flight(db, "AMU3000")
        db.commit()

        page = FlightService(db).list_flights(
            page=1,
            page_size=20,
            flight_no=" mu ",
        )

        assert page["total"] == 2
        assert [flight.flight_no for flight in page["items"]] == ["MU1001", "MU2002"]
    finally:
        db.close()


def test_list_instances_filters_by_flight_no_prefix() -> None:
    db = _make_db()
    try:
        _seed_flight(db, "9C1231")
        _seed_flight(db, "9C1232")
        _seed_flight(db, "9C9000")
        _seed_instance(db, "9C1231")
        _seed_instance(db, "9C1232")
        _seed_instance(db, "9C9000")
        db.commit()

        page = FlightService(db).list_instances(
            page=1,
            page_size=20,
            flight_no=" 9c123 ",
        )

        assert page["total"] == 2
        assert [row.flight_no for row in page["items"]] == ["9C1231", "9C1232"]
    finally:
        db.close()


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            City.__table__,
            Airport.__table__,
            Airline.__table__,
            AircraftType.__table__,
            Flight.__table__,
            FlightInstance.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _seed_flight(db: Session, flight_no: str) -> None:
    db.add(
        Flight(
            flight_no=flight_no,
            scheduled_departure=time(8, 0),
            scheduled_arrival=time(10, 0),
            fuel_infra_fee=Decimal("50.00"),
            dep_airport_code="SHA",
            arr_airport_code="PEK",
            airline_code=flight_no[:2],
            aircraft_model="A320",
        )
    )


def _seed_instance(db: Session, flight_no: str) -> None:
    db.add(
        FlightInstance(
            instance_id=f"{flight_no}_20260601",
            flight_no=flight_no,
            flight_date=date(2026, 6, 1),
            economy_left=100,
            first_left=8,
            status="计划",
        )
    )
