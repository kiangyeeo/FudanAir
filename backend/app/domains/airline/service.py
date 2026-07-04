from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import AppException, ResourceInUseError, ResourceNotFoundError
from app.domains.airline.models import AircraftType, Airline
from app.domains.airline.repository import AircraftTypeRepository, AirlineRepository
from app.domains.airline.schemas import (
    AircraftTypeCreate,
    AircraftTypeUpdate,
    AirlineCreate,
    AirlineUpdate,
)


class AirlineService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AirlineRepository(db)

    def list_all(self) -> list[Airline]:
        return self.repo.list_all()

    def get_or_404(self, iata_code: str) -> Airline:
        code = _airline_code(iata_code)
        airline = self.repo.get(code)
        if not airline:
            raise ResourceNotFoundError(f"Airline {code} does not exist")
        return airline

    def create(self, payload: AirlineCreate) -> Airline:
        code = _airline_code(payload.iata_code)
        try:
            with transaction(self.db):
                if self.repo.get(code):
                    raise AppException(f"Airline code {code} already exists")
                return self.repo.create(code, payload.airline_name)
        except IntegrityError as exc:
            raise AppException(f"Failed to create airline {code}") from exc

    def update(self, iata_code: str, payload: AirlineUpdate) -> Airline:
        code = _airline_code(iata_code)
        new_code = _airline_code(payload.iata_code) if payload.iata_code else code
        try:
            with transaction(self.db):
                airline = self.repo.get(code)
                if not airline:
                    raise ResourceNotFoundError(f"Airline {code} does not exist")
                return self._save_update(airline, code, new_code, payload)
        except IntegrityError as exc:
            raise AppException(f"Failed to update airline {code}") from exc

    def delete(self, iata_code: str) -> None:
        code = _airline_code(iata_code)
        try:
            with transaction(self.db):
                airline = self.repo.get(code)
                if not airline:
                    raise ResourceNotFoundError(f"Airline {code} does not exist")
                if self.repo.is_referenced(code):
                    raise ResourceInUseError(f"Airline {code} is referenced by flights and cannot be deleted")
                self.repo.delete(airline)
        except IntegrityError as exc:
            raise ResourceInUseError(f"Airline {code} is in use and cannot be deleted") from exc

    def _save_update(
        self,
        airline: Airline,
        old_code: str,
        new_code: str,
        payload: AirlineUpdate,
    ) -> Airline:
        self._ensure_identity_editable(airline, old_code, new_code, payload)
        if new_code == old_code:
            return self.repo.update(airline, payload.airline_name)
        if self.repo.get(new_code):
            raise AppException(f"Airline code {new_code} already exists")
        return self.repo.rename_code(airline, new_code, payload.airline_name)

    def _ensure_identity_editable(
        self,
        airline: Airline,
        old_code: str,
        new_code: str,
        payload: AirlineUpdate,
    ) -> None:
        identity_changed = new_code != old_code or airline.airline_name != payload.airline_name
        if identity_changed and self.repo.is_referenced(old_code):
            raise ResourceInUseError(f"Airline {old_code} is referenced by flights and its code or name cannot be changed")


class AircraftTypeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AircraftTypeRepository(db)

    def list_all(self) -> list[AircraftType]:
        return self.repo.list_all()

    def get_or_404(self, model: str) -> AircraftType:
        aircraft_model = _aircraft_model(model)
        aircraft_type = self.repo.get(aircraft_model)
        if not aircraft_type:
            raise ResourceNotFoundError(f"Aircraft type {aircraft_model} does not exist")
        return aircraft_type

    def create(self, payload: AircraftTypeCreate) -> AircraftType:
        aircraft_model = _aircraft_model(payload.model)
        _ensure_positive_seats(payload.economy_seats, payload.first_seats)
        try:
            with transaction(self.db):
                if self.repo.get(aircraft_model):
                    raise AppException(f"Aircraft type {aircraft_model} already exists")
                return self.repo.create(
                    aircraft_model,
                    payload.economy_seats,
                    payload.first_seats,
                )
        except IntegrityError as exc:
            raise AppException(f"Failed to create aircraft type {aircraft_model}") from exc

    def update(self, model: str, payload: AircraftTypeUpdate) -> AircraftType:
        aircraft_model = _aircraft_model(model)
        new_model = _aircraft_model(payload.model) if payload.model else aircraft_model
        _ensure_positive_seats(payload.economy_seats, payload.first_seats)
        try:
            with transaction(self.db):
                aircraft_type = self.repo.get(aircraft_model)
                if not aircraft_type:
                    raise ResourceNotFoundError(f"Aircraft type {aircraft_model} does not exist")
                return self._save_update(aircraft_type, aircraft_model, new_model, payload)
        except IntegrityError as exc:
            raise AppException(f"Failed to update aircraft type {aircraft_model}") from exc

    def delete(self, model: str) -> None:
        aircraft_model = _aircraft_model(model)
        try:
            with transaction(self.db):
                aircraft_type = self.repo.get(aircraft_model)
                if not aircraft_type:
                    raise ResourceNotFoundError(f"Aircraft type {aircraft_model} does not exist")
                if self.repo.is_referenced(aircraft_model):
                    raise ResourceInUseError(f"Aircraft type {aircraft_model} is referenced by flights and cannot be deleted")
                self.repo.delete(aircraft_type)
        except IntegrityError as exc:
            raise ResourceInUseError(f"Aircraft type {aircraft_model} is in use and cannot be deleted") from exc

    def _save_update(
        self,
        aircraft_type: AircraftType,
        old_model: str,
        new_model: str,
        payload: AircraftTypeUpdate,
    ) -> AircraftType:
        if new_model == old_model:
            return self.repo.update(
                aircraft_type,
                payload.economy_seats,
                payload.first_seats,
            )
        if self.repo.is_referenced(old_model):
            raise ResourceInUseError(f"Aircraft type {old_model} is referenced by flights and cannot be renamed")
        if self.repo.get(new_model):
            raise AppException(f"Aircraft type {new_model} already exists")
        return self.repo.rename_model(
            aircraft_type,
            new_model,
            payload.economy_seats,
            payload.first_seats,
        )


def _airline_code(iata_code: str) -> str:
    return iata_code.strip().upper()


def _aircraft_model(model: str) -> str:
    return model.strip().upper()


def _ensure_positive_seats(economy_seats: int, first_seats: int) -> None:
    if economy_seats + first_seats <= 0:
        raise AppException("Aircraft type seat total must be greater than 0.")
