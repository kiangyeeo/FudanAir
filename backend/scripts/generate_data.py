from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.constants import ECONOMY_STANDARD_RATIO
from app.core.id_generator import gen_instance_id


_MINUTES_PER_DAY = 24 * 60
_ECONOMY_BASE_PRICE = Decimal("420.00")
_ECONOMY_MINUTE_RATE = Decimal("2.10")
_ECONOMY_SPECIAL_DISCOUNT = Decimal("0.72")
_FIRST_CLASS_MULTIPLIER = Decimal("3.20")
_PRICE_STEP = Decimal("10.00")
_CENT = Decimal("0.01")


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
        economy_standard, economy_special = _split_economy_seats(int(economy_left))
        standard_price, special_price, first_price = _price_set(dep_time, arr_time)
        params.extend(
            [
                (instance_id, "经济舱", "标准", standard_price, economy_standard),
                (instance_id, "经济舱", "特价", special_price, economy_special),
            ]
        )
        if int(first_left) > 0:
            params.append((instance_id, "头等舱", "标准", first_price, int(first_left)))
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


def _split_economy_seats(total: int) -> tuple[int, int]:
    ratio = Decimal(str(ECONOMY_STANDARD_RATIO))
    standard = int((Decimal(total) * ratio).to_integral_value(rounding=ROUND_HALF_UP))
    standard = min(max(standard, 0), total)
    return standard, total - standard


def _price_set(dep_time: Any, arr_time: Any) -> tuple[Decimal, Decimal, Decimal]:
    duration = Decimal(_flight_duration_minutes(dep_time, arr_time))
    economy_price = _round_price(_ECONOMY_BASE_PRICE + _ECONOMY_MINUTE_RATE * duration)
    special_price = _round_price(economy_price * _ECONOMY_SPECIAL_DISCOUNT)
    first_price = _round_price(economy_price * _FIRST_CLASS_MULTIPLIER)
    return economy_price, special_price, first_price


def _flight_duration_minutes(dep_time: Any, arr_time: Any) -> int:
    dep_minutes = _time_to_minutes(dep_time)
    arr_minutes = _time_to_minutes(arr_time)
    if arr_minutes <= dep_minutes:
        arr_minutes += _MINUTES_PER_DAY
    return arr_minutes - dep_minutes


def _time_to_minutes(value: Any) -> int:
    if isinstance(value, timedelta):
        return int(value.total_seconds() // 60)
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, str):
        hour, minute, *_ = value.split(":")
        return int(hour) * 60 + int(minute)
    raise TypeError(f"无法解析 TIME 字段: {value!r}")


def _round_price(value: Decimal) -> Decimal:
    rounded = (value / _PRICE_STEP).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (rounded * _PRICE_STEP).quantize(_CENT)


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
