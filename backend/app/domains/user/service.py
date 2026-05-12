from __future__ import annotations

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import AppException
from app.domains.user.models import Passenger
from app.domains.user.repository import PassengerRepository


class PassengerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PassengerRepository(db)

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
