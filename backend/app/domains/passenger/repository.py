from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domains.passenger.models import Passenger


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

    def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT DISTINCT
                    p.id_no,
                    p.real_name,
                    p.birth_date
                FROM passenger p
                JOIN ticket t ON t.passenger_id = p.id_no
                JOIN aptorder o ON o.order_no = t.order_no
                WHERE o.user_id = :user_id
                ORDER BY p.real_name, p.id_no
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def belongs_to_user(self, user_id: int, id_no: str) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM ticket t
                JOIN aptorder o ON o.order_no = t.order_no
                WHERE o.user_id = :user_id
                  AND t.passenger_id = :id_no
                LIMIT 1
                """
            ),
            {"user_id": user_id, "id_no": id_no},
        ).first()
        return row is not None
