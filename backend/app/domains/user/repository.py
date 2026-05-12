from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.domains.user.models import Passenger


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
