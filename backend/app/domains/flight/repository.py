from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.domains.flight.models import (
    CabinPrice,
    Flight,
    FlightInstance,
    FlightStopover,
    FlightWeekday,
)


class FlightRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, flight_no: str) -> Flight | None:
        return self.db.get(Flight, flight_no)

    def list_page(
        self,
        page: int,
        page_size: int,
        flight_no: str | None = None,
        airline_code: str | None = None,
        dep_airport_code: str | None = None,
        arr_airport_code: str | None = None,
    ) -> tuple[list[Flight], int]:
        query = self.db.query(Flight)
        if flight_no:
            query = query.filter(Flight.flight_no.like(f"{flight_no}%"))
        if airline_code:
            query = query.filter(Flight.airline_code == airline_code)
        if dep_airport_code:
            query = query.filter(Flight.dep_airport_code == dep_airport_code)
        if arr_airport_code:
            query = query.filter(Flight.arr_airport_code == arr_airport_code)

        total = query.count()
        items = (
            query.order_by(Flight.flight_no)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, **data: Any) -> Flight:
        flight = Flight(**data)
        self.db.add(flight)
        self.db.flush()
        return flight

    def update(self, flight: Flight, **data: Any) -> Flight:
        for key, value in data.items():
            setattr(flight, key, value)
        self.db.flush()
        return flight

    def delete(self, flight: Flight) -> None:
        self.db.delete(flight)
        self.db.flush()

    def exists_airport(self, iata_code: str) -> bool:
        return self._exists("airport", "iata_code", iata_code)

    def exists_airline(self, airline_code: str) -> bool:
        return self._exists("airline", "iata_code", airline_code)

    def exists_aircraft_type(self, model: str) -> bool:
        return self._exists("aircraft_type", "model", model)

    def get_airline_name(self, airline_code: str) -> str | None:
        return self.db.execute(
            text("SELECT airline_name FROM airline WHERE iata_code = :code"),
            {"code": airline_code},
        ).scalar_one_or_none()

    def get_aircraft_seats(self, flight_no: str) -> tuple[int, int] | None:
        row = self.db.execute(
            text(
                """
                SELECT at.economy_seats, at.first_seats
                FROM flight f
                JOIN aircraft_type at ON f.aircraft_model = at.model
                WHERE f.flight_no = :flight_no
                """
            ),
            {"flight_no": flight_no},
        ).first()
        if not row:
            return None
        return int(row.economy_seats), int(row.first_seats)

    def has_instances(self, flight_no: str) -> bool:
        row = (
            self.db.query(FlightInstance.instance_id)
            .filter(FlightInstance.flight_no == flight_no)
            .first()
        )
        return row is not None

    def replace_weekdays(self, flight_no: str, weekdays: Iterable[int]) -> None:
        self.db.execute(delete(FlightWeekday).where(FlightWeekday.flight_no == flight_no))
        for weekday in weekdays:
            self.db.add(FlightWeekday(flight_no=flight_no, weekday=weekday))
        self.db.flush()

    def get_weekdays(self, flight_no: str) -> list[int]:
        rows = (
            self.db.query(FlightWeekday.weekday)
            .filter(FlightWeekday.flight_no == flight_no)
            .order_by(FlightWeekday.weekday)
            .all()
        )
        return [int(row.weekday) for row in rows]

    def replace_stopovers(self, flight_no: str, airport_codes: Iterable[str]) -> None:
        self.db.execute(delete(FlightStopover).where(FlightStopover.flight_no == flight_no))
        for index, airport_code in enumerate(airport_codes, start=1):
            self.db.add(
                FlightStopover(
                    flight_no=flight_no,
                    stop_order=index,
                    airport_code=airport_code,
                )
            )
        self.db.flush()

    def get_stopovers(self, flight_no: str) -> list[str]:
        rows = (
            self.db.query(FlightStopover.airport_code)
            .filter(FlightStopover.flight_no == flight_no)
            .order_by(FlightStopover.stop_order)
            .all()
        )
        return [str(row.airport_code) for row in rows]

    def _exists(self, table_name: str, field_name: str, value: str) -> bool:
        row = self.db.execute(
            text(
                f"""
                SELECT 1
                FROM {table_name}
                WHERE {field_name} = :value
                LIMIT 1
                """
            ),
            {"value": value},
        ).first()
        return row is not None


class FlightInstanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, instance_id: str) -> FlightInstance | None:
        return self.db.get(FlightInstance, instance_id)

    def get_by_flight_date(
        self,
        flight_no: str,
        flight_date: date,
    ) -> FlightInstance | None:
        return (
            self.db.query(FlightInstance)
            .filter(
                FlightInstance.flight_no == flight_no,
                FlightInstance.flight_date == flight_date,
            )
            .first()
        )

    def list_page(
        self,
        page: int,
        page_size: int,
        flight_no: str | None = None,
        flight_date: date | None = None,
        status: str | None = None,
    ) -> tuple[list[FlightInstance], int]:
        query = self.db.query(FlightInstance)
        if flight_no:
            query = query.filter(FlightInstance.flight_no.like(f"{flight_no}%"))
        if flight_date:
            query = query.filter(FlightInstance.flight_date == flight_date)
        if status:
            query = query.filter(FlightInstance.status == status)

        total = query.count()
        items = (
            query.order_by(FlightInstance.flight_date, FlightInstance.flight_no)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(
        self,
        instance_id: str,
        flight_no: str,
        flight_date: date,
        economy_left: int,
        first_left: int,
        status: str,
    ) -> FlightInstance:
        instance = FlightInstance(
            instance_id=instance_id,
            flight_no=flight_no,
            flight_date=flight_date,
            economy_left=economy_left,
            first_left=first_left,
            status=status,
        )
        self.db.add(instance)
        self.db.flush()
        return instance

    def update_status(self, instance: FlightInstance, status: str) -> FlightInstance:
        instance.status = status
        self.db.flush()
        return instance

    def delete(self, instance: FlightInstance) -> None:
        self.db.delete(instance)
        self.db.flush()

    def has_tickets(self, instance_id: str) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM ticket
                WHERE instance_id = :instance_id
                LIMIT 1
                """
            ),
            {"instance_id": instance_id},
        ).first()
        return row is not None

    def adjust_seats(self, instance_id: str, cabin_class: str, delta: int) -> bool:
        field_name = "economy_left" if cabin_class == "经济舱" else "first_left"
        if delta >= 0:
            result = self.db.execute(
                text(
                    f"""
                    UPDATE flight_instance
                    SET {field_name} = {field_name} + :amount
                    WHERE instance_id = :instance_id
                    """
                ),
                {"instance_id": instance_id, "amount": delta},
            )
            self.db.flush()
            return int(result.rowcount or 0) == 1

        amount = abs(delta)
        result = self.db.execute(
            text(
                f"""
                UPDATE flight_instance
                SET {field_name} = {field_name} - :amount
                WHERE instance_id = :instance_id
                  AND {field_name} >= :amount
                """
            ),
            {"instance_id": instance_id, "amount": amount},
        )
        self.db.flush()
        return int(result.rowcount or 0) == 1

    def set_seat_summary(self, instance_id: str, economy_left: int, first_left: int) -> None:
        self.db.execute(
            text(
                """
                UPDATE flight_instance
                SET economy_left = :economy_left,
                    first_left = :first_left
                WHERE instance_id = :instance_id
                """
            ),
            {
                "instance_id": instance_id,
                "economy_left": economy_left,
                "first_left": first_left,
            },
        )
        self.db.flush()

    def detail_context(self, instance_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    fi.instance_id,
                    fi.flight_no,
                    fi.flight_date,
                    fi.economy_left,
                    fi.first_left,
                    fi.status,
                    f.scheduled_departure,
                    f.scheduled_arrival,
                    f.fuel_infra_fee,
                    f.dep_airport_code,
                    f.arr_airport_code,
                    f.airline_code,
                    al.airline_name
                FROM flight_instance fi
                JOIN flight f ON fi.flight_no = f.flight_no
                JOIN airline al ON f.airline_code = al.iata_code
                WHERE fi.instance_id = :instance_id
                """
            ),
            {"instance_id": instance_id},
        ).mappings().first()
        return dict(row) if row else None


class CabinPriceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
    ) -> CabinPrice | None:
        return self.db.get(CabinPrice, (instance_id, cabin_class, fare_type))

    def lock(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
    ) -> CabinPrice | None:
        stmt = (
            select(CabinPrice)
            .where(
                CabinPrice.instance_id == instance_id,
                CabinPrice.cabin_class == cabin_class,
                CabinPrice.fare_type == fare_type,
            )
            .with_for_update()
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_instance(self, instance_id: str) -> list[CabinPrice]:
        return (
            self.db.query(CabinPrice)
            .filter(CabinPrice.instance_id == instance_id)
            .order_by(CabinPrice.cabin_class, CabinPrice.fare_type)
            .all()
        )

    def create(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        price: Decimal,
        available_seats: int,
    ) -> CabinPrice:
        cabin_price = CabinPrice(
            instance_id=instance_id,
            cabin_class=cabin_class,
            fare_type=fare_type,
            price=price,
            available_seats=available_seats,
        )
        self.db.add(cabin_price)
        self.db.flush()
        return cabin_price

    def replace_all(
        self,
        instance_id: str,
        rows: Iterable[dict[str, Any]],
    ) -> list[CabinPrice]:
        current = {
            (item.cabin_class, item.fare_type): item
            for item in self.list_by_instance(instance_id)
        }
        created: list[CabinPrice] = []
        kept_keys: set[tuple[str, str]] = set()

        for row in rows:
            key = (row["cabin_class"], row["fare_type"])
            kept_keys.add(key)
            cabin_price = current.get(key)
            if cabin_price:
                cabin_price.price = row["price"]
                cabin_price.available_seats = row["available_seats"]
                created.append(cabin_price)
                continue
            created.append(
                self.create(
                    instance_id,
                    row["cabin_class"],
                    row["fare_type"],
                    row["price"],
                    row["available_seats"],
                )
            )

        for key, cabin_price in current.items():
            if key not in kept_keys:
                self.db.delete(cabin_price)

        self.db.flush()
        return created

    def update_available(self, cabin_price: CabinPrice, quantity_delta: int) -> CabinPrice:
        cabin_price.available_seats = int(cabin_price.available_seats) + quantity_delta
        self.db.flush()
        return cabin_price

    def sum_by_cabin(self, instance_id: str) -> dict[str, int]:
        rows = (
            self.db.query(
                CabinPrice.cabin_class,
                func.coalesce(func.sum(CabinPrice.available_seats), 0).label("seat_count"),
            )
            .filter(CabinPrice.instance_id == instance_id)
            .group_by(CabinPrice.cabin_class)
            .all()
        )
        return {str(row.cabin_class): int(row.seat_count) for row in rows}
