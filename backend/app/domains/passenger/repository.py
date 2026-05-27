from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domains.passenger.models import Passenger, UserPassenger


class PassengerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id_no: str) -> Passenger | None:
        return self.db.get(Passenger, id_no)

    def create(self, id_no: str, real_name: str, birth_date: date) -> Passenger:
        passenger = Passenger(id_no=id_no, real_name=real_name, birth_date=birth_date)
        self.db.add(passenger)
        self.db.flush()
        return passenger

    def update(self, passenger: Passenger, real_name: str, birth_date: date) -> Passenger:
        passenger.real_name = real_name
        passenger.birth_date = birth_date
        self.db.flush()
        return passenger

    def bind_to_user(self, user_id: int, id_no: str) -> UserPassenger:
        binding = self.get_binding(user_id, id_no)
        if binding:
            return binding
        binding = UserPassenger(user_id=user_id, id_no=id_no)
        self.db.add(binding)
        self.db.flush()
        return binding

    def unbind_from_user(self, user_id: int, id_no: str) -> bool:
        binding = self.get_binding(user_id, id_no)
        if not binding:
            return False
        self.db.delete(binding)
        self.db.flush()
        return True

    def get_binding(self, user_id: int, id_no: str) -> UserPassenger | None:
        return self.db.get(UserPassenger, (user_id, id_no))

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT
                    p.id_no,
                    p.real_name,
                    p.birth_date
                FROM user_passenger up
                JOIN passenger p ON p.id_no = up.id_no
                WHERE up.user_id = :user_id
                ORDER BY up.created_at DESC, p.real_name, p.id_no
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def belongs_to_user(self, user_id: int, id_no: str) -> bool:
        return self.get_binding(user_id, id_no) is not None
