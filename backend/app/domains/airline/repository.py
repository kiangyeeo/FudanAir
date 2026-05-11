from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domains.airline.models import AircraftType, Airline


class AirlineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, iata_code: str) -> Airline | None:
        return self.db.get(Airline, iata_code)

    def list_all(self) -> list[Airline]:
        return self.db.query(Airline).order_by(Airline.iata_code).all()

    def create(self, iata_code: str, airline_name: str) -> Airline:
        airline = Airline(iata_code=iata_code, airline_name=airline_name)
        self.db.add(airline)
        self.db.flush()
        return airline

    def update(self, airline: Airline, airline_name: str) -> Airline:
        airline.airline_name = airline_name
        self.db.flush()
        return airline

    def delete(self, airline: Airline) -> None:
        self.db.delete(airline)
        self.db.flush()

    def is_referenced(self, iata_code: str) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM flight
                WHERE airline_code = :iata_code
                LIMIT 1
                """
            ),
            {"iata_code": iata_code},
        ).first()
        return row is not None


class AircraftTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, model: str) -> AircraftType | None:
        return self.db.get(AircraftType, model)

    def list_all(self) -> list[AircraftType]:
        return self.db.query(AircraftType).order_by(AircraftType.model).all()

    def create(
        self,
        model: str,
        economy_seats: int,
        first_seats: int,
    ) -> AircraftType:
        aircraft_type = AircraftType(
            model=model,
            economy_seats=economy_seats,
            first_seats=first_seats,
        )
        self.db.add(aircraft_type)
        self.db.flush()
        return aircraft_type

    def update(
        self,
        aircraft_type: AircraftType,
        economy_seats: int,
        first_seats: int,
    ) -> AircraftType:
        aircraft_type.economy_seats = economy_seats
        aircraft_type.first_seats = first_seats
        self.db.flush()
        return aircraft_type

    def delete(self, aircraft_type: AircraftType) -> None:
        self.db.delete(aircraft_type)
        self.db.flush()

    def is_referenced(self, model: str) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM flight
                WHERE aircraft_model = :model
                LIMIT 1
                """
            ),
            {"model": model},
        ).first()
        return row is not None
