from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domains.city.models import Airport, City, CityNearApt


class CityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, city_name: str) -> City | None:
        return self.db.get(City, city_name)

    def list_names(self) -> list[str]:
        rows = self.db.query(City.city_name).order_by(City.city_name).all()
        return [row.city_name for row in rows]

    def create(self, city_name: str) -> City:
        city = City(city_name=city_name)
        self.db.add(city)
        self.db.flush()
        return city

    def rename(self, old_name: str, new_name: str) -> City:
        new_city = self.create(new_name)
        self.db.query(Airport).filter(Airport.city_name == old_name).update(
            {Airport.city_name: new_name},
            synchronize_session=False,
        )
        self.db.query(CityNearApt).filter(CityNearApt.city_name == old_name).update(
            {CityNearApt.city_name: new_name},
            synchronize_session=False,
        )
        old_city = self.get(old_name)
        if old_city:
            self.db.delete(old_city)
        self.db.flush()
        return new_city

    def delete(self, city: City) -> None:
        self.db.delete(city)
        self.db.flush()

    def has_airport(self, city_name: str) -> bool:
        return (
            self.db.query(Airport.iata_code)
            .filter(Airport.city_name == city_name)
            .first()
            is not None
        )


class AirportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, iata_code: str) -> Airport | None:
        return self.db.get(Airport, iata_code)

    def list_all(self, city_name: str | None = None) -> list[Airport]:
        query = self.db.query(Airport)
        if city_name:
            query = query.filter(Airport.city_name == city_name)
        return query.order_by(Airport.iata_code).all()

    def create(self, iata_code: str, airport_name: str, city_name: str) -> Airport:
        airport = Airport(
            iata_code=iata_code,
            airport_name=airport_name,
            city_name=city_name,
        )
        self.db.add(airport)
        self.db.flush()
        return airport

    def update(self, airport: Airport, airport_name: str, city_name: str) -> Airport:
        airport.airport_name = airport_name
        airport.city_name = city_name
        self.db.flush()
        return airport

    def delete(self, airport: Airport) -> None:
        self.db.delete(airport)
        self.db.flush()

    def is_referenced(self, iata_code: str) -> bool:
        flight_ref = self.db.execute(
            text(
                """
                SELECT 1
                FROM flight
                WHERE dep_airport_code = :iata_code
                   OR arr_airport_code = :iata_code
                LIMIT 1
                """
            ),
            {"iata_code": iata_code},
        ).first()
        stopover_ref = self.db.execute(
            text(
                """
                SELECT 1
                FROM flight_stopover
                WHERE airport_code = :iata_code
                LIMIT 1
                """
            ),
            {"iata_code": iata_code},
        ).first()
        return flight_ref is not None or stopover_ref is not None


class CityNearAirportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, city_name: str, iata_code: str) -> CityNearApt | None:
        return self.db.get(CityNearApt, (city_name, iata_code))

    def list_by_city(self, city_name: str) -> list[dict[str, object]]:
        rows = (
            self.db.query(
                CityNearApt.iata_code,
                Airport.airport_name,
                CityNearApt.distance,
            )
            .join(Airport, Airport.iata_code == CityNearApt.iata_code)
            .filter(CityNearApt.city_name == city_name)
            .order_by(CityNearApt.distance, CityNearApt.iata_code)
            .all()
        )
        return [
            {
                "iata_code": row.iata_code,
                "airport_name": row.airport_name,
                "distance": float(row.distance),
            }
            for row in rows
        ]

    def create(self, city_name: str, iata_code: str, distance: Decimal) -> CityNearApt:
        relation = CityNearApt(
            city_name=city_name,
            iata_code=iata_code,
            distance=distance,
        )
        self.db.add(relation)
        self.db.flush()
        return relation

    def upsert(self, city_name: str, iata_code: str, distance: Decimal) -> CityNearApt:
        relation = self.get(city_name, iata_code)
        if relation:
            relation.distance = distance
            self.db.flush()
            return relation
        return self.create(city_name, iata_code, distance)

    def delete(self, relation: CityNearApt) -> None:
        self.db.delete(relation)
        self.db.flush()

    def delete_own_relation(self, city_name: str, iata_code: str) -> None:
        relation = self.get(city_name, iata_code)
        if relation and relation.distance == Decimal("0.00"):
            self.delete(relation)
