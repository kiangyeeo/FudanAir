from __future__ import annotations

import sys
from datetime import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.domains.airline.models import AircraftType, Airline
from app.domains.city.models import Airport, City
from app.domains.flight.models import Flight
from app.domains.flight.service import FlightService


def test_list_flights_filters_by_flight_no() -> None:
    db = _make_db()
    try:
        _seed_flight(db, "CA1001")
        _seed_flight(db, "MU2002")
        db.commit()

        page = FlightService(db).list_flights(
            page=1,
            page_size=20,
            flight_no=" ca1001 ",
        )

        assert page["total"] == 1
        assert [flight.flight_no for flight in page["items"]] == ["CA1001"]
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
