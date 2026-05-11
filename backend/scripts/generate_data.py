from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.id_generator import gen_instance_id
from app.domains.flight.pricing import default_cabin_price_specs


def generate_flight_instances(
    cur: Any,
    start_date: date | None = None,
    days: int | None = None,
) -> int:
    start = start_date or date.today()
    total_days = days if days is not None else settings.INSTANCE_AHEAD_DAYS
    if total_days <= 0:
        return 0

    flights_by_weekday = _fetch_flights_by_weekday(cur)
    params = []
    for offset in range(total_days):
        flight_date = start + timedelta(days=offset)
        for flight_no, economy_seats, first_seats in flights_by_weekday[flight_date.isoweekday()]:
            params.append(
                (
                    gen_instance_id(flight_no, flight_date),
                    flight_no,
                    flight_date,
                    economy_seats,
                    first_seats,
                    "可订",
                )
            )
    return _executemany(cur, _insert_instance_sql(), params)


def generate_cabin_prices(cur: Any) -> int:
    params = []
    for instance_id, economy_left, first_left, dep_time, arr_time in _fetch_instances(cur):
        for spec in default_cabin_price_specs(
            int(economy_left),
            int(first_left),
            dep_time,
            arr_time,
        ):
            params.append(
                (
                    instance_id,
                    spec.cabin_class,
                    spec.fare_type,
                    spec.price,
                    spec.available_seats,
                )
            )
    return _executemany(cur, _insert_cabin_price_sql(), params)


def _fetch_flights_by_weekday(cur: Any) -> dict[int, list[tuple[str, int, int]]]:
    cur.execute(
        """
        SELECT fw.weekday, f.flight_no, at.economy_seats, at.first_seats
        FROM flight f
        JOIN flight_weekday fw ON f.flight_no = fw.flight_no
        JOIN aircraft_type at ON f.aircraft_model = at.model
        ORDER BY fw.weekday, f.flight_no
        """
    )
    result: dict[int, list[tuple[str, int, int]]] = defaultdict(list)
    for weekday, flight_no, economy_seats, first_seats in cur.fetchall():
        result[int(weekday)].append((flight_no, int(economy_seats), int(first_seats)))
    return result


def _fetch_instances(cur: Any) -> list[tuple[Any, ...]]:
    cur.execute(
        """
        SELECT
            fi.instance_id, fi.economy_left, fi.first_left,
            f.scheduled_departure, f.scheduled_arrival
        FROM flight_instance fi
        JOIN flight f ON fi.flight_no = f.flight_no
        ORDER BY fi.instance_id
        """
    )
    return list(cur.fetchall())


def _executemany(cur: Any, sql: str, params: list[tuple[Any, ...]]) -> int:
    if not params:
        return 0
    cur.executemany(sql, params)
    return int(cur.rowcount)


def _insert_instance_sql() -> str:
    return """
        INSERT IGNORE INTO flight_instance (
            instance_id, flight_no, flight_date, economy_left, first_left, status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """


def _insert_cabin_price_sql() -> str:
    return """
        INSERT IGNORE INTO cabin_price (
            instance_id, cabin_class, fare_type, price, available_seats
        )
        VALUES (%s, %s, %s, %s, %s)
    """
