from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import AppException, ResourceNotFoundError
from app.domains.passenger.models import Passenger
from app.domains.passenger.repository import PassengerRepository
from app.domains.passenger.schemas import PassengerUpdate


class PassengerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PassengerRepository(db)

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        return self.repo.list_by_user(user_id)

    def upsert(self, id_no: str, real_name: str, birth_date: date) -> Passenger:
        normalized_id = id_no.strip()
        normalized_name = real_name.strip()
        try:
            with transaction(self.db):
                passenger = self.repo.get(normalized_id)
                if passenger:
                    return self.repo.update(passenger, normalized_name, birth_date)
                return self.repo.create(normalized_id, normalized_name, birth_date)
        except IntegrityError as exc:
            raise AppException("乘机人保存失败") from exc

    def update(self, user_id: int, id_no: str, payload: PassengerUpdate) -> Passenger:
        normalized_id = id_no.strip()
        try:
            with transaction(self.db):
                if not self.repo.belongs_to_user(user_id, normalized_id):
                    raise ResourceNotFoundError(f"乘机人 {normalized_id} 不存在")
                passenger = self.repo.get(normalized_id)
                if not passenger:
                    raise ResourceNotFoundError(f"乘机人 {normalized_id} 不存在")
                return self.repo.update(
                    passenger,
                    payload.real_name.strip(),
                    payload.birth_date,
                )
        except IntegrityError as exc:
            raise AppException(f"乘机人 {normalized_id} 更新失败") from exc
