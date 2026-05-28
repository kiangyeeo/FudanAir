from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.core.exceptions import ResourceInUseError
from app.domains.airline.models import AircraftType
from app.domains.airline.schemas import AircraftTypeUpdate
from app.domains.airline.service import AircraftTypeService


def test_update_aircraft_type_model_when_unreferenced() -> None:
    db = _make_db()
    try:
        _seed_aircraft_type(db, "A320", 160, 8)
        db.commit()

        aircraft_type = AircraftTypeService(db).update(
            "A320",
            AircraftTypeUpdate(model="b738", economy_seats=170, first_seats=10),
        )

        assert aircraft_type.model == "B738"
        assert aircraft_type.economy_seats == 170
        assert aircraft_type.first_seats == 10
        assert db.get(AircraftType, "A320") is None
        assert db.get(AircraftType, "B738").economy_seats == 170
    finally:
        db.close()


def test_update_aircraft_type_model_rejects_referenced_type() -> None:
    db = _make_db()
    try:
        _seed_aircraft_type(db, "A320", 160, 8)
        _seed_flight_reference(db, "A320")
        db.commit()

        with pytest.raises(ResourceInUseError):
            AircraftTypeService(db).update(
                "A320",
                AircraftTypeUpdate(model="B738", economy_seats=160, first_seats=8),
            )

        assert db.get(AircraftType, "A320") is not None
        assert db.get(AircraftType, "B738") is None
    finally:
        db.close()


def test_update_aircraft_type_seats_keeps_existing_reference_rule() -> None:
    db = _make_db()
    try:
        _seed_aircraft_type(db, "A320", 160, 8)
        _seed_flight_reference(db, "A320")
        db.commit()

        aircraft_type = AircraftTypeService(db).update(
            "A320",
            AircraftTypeUpdate(model="A320", economy_seats=168, first_seats=8),
        )

        assert aircraft_type.model == "A320"
        assert aircraft_type.economy_seats == 168
    finally:
        db.close()


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[AircraftType.__table__])
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE flight (aircraft_model VARCHAR(32))"))
    return sessionmaker(bind=engine)()


def _seed_aircraft_type(db: Session, model: str, economy_seats: int, first_seats: int) -> None:
    db.add(
        AircraftType(
            model=model,
            economy_seats=economy_seats,
            first_seats=first_seats,
        )
    )


def _seed_flight_reference(db: Session, model: str) -> None:
    db.execute(
        text("INSERT INTO flight (aircraft_model) VALUES (:model)"),
        {"model": model},
    )
