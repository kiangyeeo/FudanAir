from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import AppException, ResourceNotFoundError
from app.domains.passenger.models import Passenger
from app.domains.passenger.repository import PassengerRepository
from app.domains.passenger.schemas import PassengerCreate, PassengerUpdate


class PassengerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PassengerRepository(db)

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self.repo.list_by_user(user_id)

    def upsert(self, id_no: str, real_name: str, birth_date: date) -> Passenger:
        normalized_id = _normalize_id(id_no)
        normalized_name = _normalize_name(real_name)
        try:
            with transaction(self.db):
                return self._upsert_passenger(normalized_id, normalized_name, birth_date)
        except IntegrityError as exc:
            raise AppException("Failed to save passenger.") from exc

    def create(self, user_id: int, payload: PassengerCreate) -> Passenger:
        return self.save_for_user(user_id, payload.id_no, payload.real_name, payload.birth_date)

    def save_for_user(
        self,
        user_id: int,
        id_no: str,
        real_name: str,
        birth_date: date,
    ) -> Passenger:
        normalized_id = _normalize_id(id_no)
        normalized_name = _normalize_name(real_name)
        try:
            with transaction(self.db):
                passenger = self._upsert_passenger(normalized_id, normalized_name, birth_date)
                self.repo.bind_to_user(user_id, normalized_id)
                return passenger
        except IntegrityError as exc:
            raise AppException("Failed to save passenger.") from exc

    def update(self, user_id: int, id_no: str, payload: PassengerUpdate) -> Passenger:
        old_id = _normalize_id(id_no)
        new_id = _normalize_id(payload.id_no or id_no)
        normalized_name = _normalize_name(payload.real_name)
        try:
            with transaction(self.db):
                if not self.repo.belongs_to_user(user_id, old_id):
                    raise ResourceNotFoundError(f"Passenger {old_id} does not exist")
                passenger = self._upsert_passenger(new_id, normalized_name, payload.birth_date)
                if new_id != old_id:
                    self.repo.bind_to_user(user_id, new_id)
                    self.repo.unbind_from_user(user_id, old_id)
                return passenger
        except IntegrityError as exc:
            raise AppException(f"Failed to update passenger {old_id}") from exc

    def delete(self, user_id: int, id_no: str) -> None:
        normalized_id = _normalize_id(id_no)
        with transaction(self.db):
            if not self.repo.unbind_from_user(user_id, normalized_id):
                raise ResourceNotFoundError(f"Passenger {normalized_id} does not exist")

    def _upsert_passenger(self, id_no: str, real_name: str, birth_date: date) -> Passenger:
        passenger = self.repo.get(id_no)
        if passenger:
            return self.repo.update(passenger, real_name, birth_date)
        return self.repo.create(id_no, real_name, birth_date)


def _normalize_id(id_no: str) -> str:
    return id_no.strip()


def _normalize_name(real_name: str) -> str:
    return real_name.strip()
