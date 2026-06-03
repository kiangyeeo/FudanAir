from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.core.exceptions import ResourceInUseError
from app.domains.city.models import Airport, City, CityNearApt
from app.domains.city.schemas import AirportUpdate
from app.domains.city.service import AirportService


def test_update_airport_iata_moves_near_airport_relations_when_unreferenced() -> None:
    db = _make_db()
    try:
        _seed_airport(db, "AAA", "原机场", "测试城市")
        db.add(City(city_name="周边城市"))
        db.add(CityNearApt(city_name="周边城市", iata_code="AAA", distance=Decimal("80.00")))
        db.commit()

        airport = AirportService(db).update(
            "AAA",
            AirportUpdate(
                iata_code="bbb",
                airport_name="新机场",
                city_name="测试城市",
            ),
        )

        assert airport.iata_code == "BBB"
        assert db.get(Airport, "AAA") is None
        assert db.get(Airport, "BBB").airport_name == "新机场"
        assert db.get(CityNearApt, ("测试城市", "BBB")).distance == Decimal("0.00")
        assert db.get(CityNearApt, ("周边城市", "BBB")).distance == Decimal("80.00")
        assert db.get(CityNearApt, ("测试城市", "AAA")) is None
    finally:
        db.close()


def test_update_airport_iata_rejects_flight_referenced_airport() -> None:
    db = _make_db()
    try:
        _seed_airport(db, "AAA", "原机场", "测试城市")
        _seed_flight_reference(db, "AAA")
        db.commit()

        with pytest.raises(ResourceInUseError):
            AirportService(db).update(
                "AAA",
                AirportUpdate(
                    iata_code="CCC",
                    airport_name="新机场",
                    city_name="测试城市",
                ),
            )

        assert db.get(Airport, "AAA") is not None
        assert db.get(Airport, "CCC") is None
    finally:
        db.close()


def test_update_airport_name_rejects_flight_referenced_airport() -> None:
    db = _make_db()
    try:
        _seed_airport(db, "AAA", "原机场", "测试城市")
        _seed_flight_reference(db, "AAA")
        db.commit()

        with pytest.raises(ResourceInUseError):
            AirportService(db).update(
                "AAA",
                AirportUpdate(
                    iata_code="AAA",
                    airport_name="新机场",
                    city_name="测试城市",
                ),
            )

        assert db.get(Airport, "AAA").airport_name == "原机场"
    finally:
        db.close()


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[City.__table__, Airport.__table__, CityNearApt.__table__])
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE flight (dep_airport_code VARCHAR(3), arr_airport_code VARCHAR(3))"))
        conn.execute(text("CREATE TABLE flight_stopover (airport_code VARCHAR(3))"))
    return sessionmaker(bind=engine)()


def _seed_airport(db: Session, iata_code: str, airport_name: str, city_name: str) -> None:
    db.add(City(city_name=city_name))
    db.add(Airport(iata_code=iata_code, airport_name=airport_name, city_name=city_name))
    db.add(CityNearApt(city_name=city_name, iata_code=iata_code, distance=Decimal("0.00")))


def _seed_flight_reference(db: Session, iata_code: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO flight (dep_airport_code, arr_airport_code)
            VALUES (:iata_code, 'BBB')
            """
        ),
        {"iata_code": iata_code},
    )
