from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.core.exceptions import ResourceInUseError
from app.domains.airline.models import Airline
from app.domains.airline.schemas import AirlineUpdate
from app.domains.airline.service import AirlineService


def test_update_airline_identity_when_unreferenced() -> None:
    db = _make_db()
    try:
        _seed_airline(db, "AA", "原航司")
        db.commit()

        airline = AirlineService(db).update(
            "AA",
            AirlineUpdate(iata_code="bb", airline_name="新航司"),
        )

        assert airline.iata_code == "BB"
        assert airline.airline_name == "新航司"
        assert db.get(Airline, "AA") is None
        assert db.get(Airline, "BB").airline_name == "新航司"
    finally:
        db.close()


def test_update_airline_code_rejects_referenced_airline() -> None:
    db = _make_db()
    try:
        _seed_airline(db, "AA", "原航司")
        _seed_flight_reference(db, "AA")
        db.commit()

        with pytest.raises(ResourceInUseError):
            AirlineService(db).update(
                "AA",
                AirlineUpdate(iata_code="BB", airline_name="原航司"),
            )

        assert db.get(Airline, "AA") is not None
        assert db.get(Airline, "BB") is None
    finally:
        db.close()


def test_update_airline_name_rejects_referenced_airline() -> None:
    db = _make_db()
    try:
        _seed_airline(db, "AA", "原航司")
        _seed_flight_reference(db, "AA")
        db.commit()

        with pytest.raises(ResourceInUseError):
            AirlineService(db).update(
                "AA",
                AirlineUpdate(iata_code="AA", airline_name="新航司"),
            )

        assert db.get(Airline, "AA").airline_name == "原航司"
    finally:
        db.close()


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Airline.__table__])
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE flight (airline_code VARCHAR(2))"))
    return sessionmaker(bind=engine)()


def _seed_airline(db: Session, iata_code: str, airline_name: str) -> None:
    db.add(Airline(iata_code=iata_code, airline_name=airline_name))


def _seed_flight_reference(db: Session, iata_code: str) -> None:
    db.execute(
        text("INSERT INTO flight (airline_code) VALUES (:iata_code)"),
        {"iata_code": iata_code},
    )
