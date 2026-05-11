from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.constants import NEARBY_DISTANCE_MAX_KM


DATA_DIR = BACKEND_DIR / "data"


def _read_csv(file_name: str, headers: list[str]) -> list[dict[str, str]]:
    path = DATA_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != headers:
            raise ValueError(
                f"{file_name} 表头应为 {headers}, 实际为 {reader.fieldnames}"
            )
        return [_clean_row(row, headers) for row in reader if _has_data(row)]


def _clean_row(row: dict[str, str], headers: list[str]) -> dict[str, str]:
    return {
        header: (row.get(header) or "").strip()
        for header in headers
    }


def _has_data(row: dict[str, str]) -> bool:
    return any((value or "").strip() for value in row.values())


def _required(row: dict[str, str], field: str) -> str:
    value = row[field]
    if not value:
        raise ValueError(f"CSV 字段 {field} 不能为空: {row}")
    return value


def _nullable(row: dict[str, str], field: str) -> str | None:
    value = row[field]
    return value or None


def _int_value(row: dict[str, str], field: str) -> int:
    return int(_required(row, field))


def _decimal_value(row: dict[str, str], field: str) -> Decimal:
    return Decimal(_required(row, field))


def _distance_value(row: dict[str, str]) -> Decimal:
    distance = _decimal_value(row, "distance")
    if distance < 0 or distance > NEARBY_DISTANCE_MAX_KM:
        raise ValueError(f"临近机场距离超出范围: {row}")
    return distance


def _executemany(cur: Any, sql: str, params: list[tuple[Any, ...]]) -> int:
    if not params:
        return 0
    cur.executemany(sql, params)
    return len(params)


def load_cities(cur: Any) -> int:
    rows = _read_csv("cities.csv", ["city_name"])
    params = [(_required(row, "city_name"),) for row in rows]
    return _executemany(cur, "INSERT INTO city (city_name) VALUES (%s)", params)


def load_airports(cur: Any) -> int:
    rows = _read_csv("airports.csv", ["iata_code", "airport_name", "city_name"])
    params = [
        (
            _required(row, "iata_code"),
            _required(row, "airport_name"),
            _required(row, "city_name"),
        )
        for row in rows
    ]
    return _executemany(cur, _airport_sql(), params)


def load_city_near_apt(cur: Any) -> int:
    rows = _read_csv("city_near_apt.csv", ["city_name", "iata_code", "distance"])
    params = [
        (_required(row, "city_name"), _required(row, "iata_code"), _distance_value(row))
        for row in rows
    ]
    return _executemany(cur, _city_near_apt_sql(), params)


def load_airlines(cur: Any) -> int:
    rows = _read_csv("airlines.csv", ["iata_code", "airline_name"])
    params = [
        (_required(row, "iata_code"), _required(row, "airline_name"))
        for row in rows
    ]
    return _executemany(cur, _airline_sql(), params)


def load_aircraft_types(cur: Any) -> int:
    rows = _read_csv("aircraft_types.csv", ["model", "economy_seats", "first_seats"])
    params = [
        (
            _required(row, "model"),
            _int_value(row, "economy_seats"),
            _int_value(row, "first_seats"),
        )
        for row in rows
    ]
    return _executemany(cur, _aircraft_type_sql(), params)


def load_flights(cur: Any) -> int:
    headers = [
        "flight_no", "scheduled_departure", "scheduled_arrival",
        "fuel_infra_fee", "dep_airport_code", "dep_terminal",
        "arr_airport_code", "arr_terminal", "airline_code", "aircraft_model",
    ]
    rows = _read_csv("flights.csv", headers)
    params = [_flight_params(row) for row in rows]
    return _executemany(cur, _flight_sql(), params)


def load_flight_weekdays(cur: Any) -> int:
    rows = _read_csv("flight_weekdays.csv", ["flight_no", "weekday"])
    params = [
        (_required(row, "flight_no"), _int_value(row, "weekday"))
        for row in rows
    ]
    return _executemany(cur, _flight_weekday_sql(), params)


def load_flight_stopovers(cur: Any) -> int:
    rows = _read_csv("flight_stopovers.csv", ["flight_no", "stop_order", "airport_code"])
    params = [
        (
            _required(row, "flight_no"),
            _int_value(row, "stop_order"),
            _required(row, "airport_code"),
        )
        for row in rows
    ]
    return _executemany(cur, _flight_stopover_sql(), params)


def _flight_params(row: dict[str, str]) -> tuple[Any, ...]:
    return (
        _required(row, "flight_no"),
        _required(row, "scheduled_departure"),
        _required(row, "scheduled_arrival"),
        _decimal_value(row, "fuel_infra_fee"),
        _required(row, "dep_airport_code"),
        _nullable(row, "dep_terminal"),
        _required(row, "arr_airport_code"),
        _nullable(row, "arr_terminal"),
        _required(row, "airline_code"),
        _required(row, "aircraft_model"),
    )


def _airport_sql() -> str:
    return """
        INSERT INTO airport (iata_code, airport_name, city_name)
        VALUES (%s, %s, %s)
    """


def _city_near_apt_sql() -> str:
    return """
        INSERT INTO city_near_apt (city_name, iata_code, distance)
        VALUES (%s, %s, %s)
    """


def _airline_sql() -> str:
    return """
        INSERT INTO airline (iata_code, airline_name)
        VALUES (%s, %s)
    """


def _aircraft_type_sql() -> str:
    return """
        INSERT INTO aircraft_type (model, economy_seats, first_seats)
        VALUES (%s, %s, %s)
    """


def _flight_sql() -> str:
    return """
        INSERT INTO flight (
            flight_no, scheduled_departure, scheduled_arrival, fuel_infra_fee,
            dep_airport_code, dep_terminal, arr_airport_code, arr_terminal,
            airline_code, aircraft_model
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """


def _flight_weekday_sql() -> str:
    return """
        INSERT INTO flight_weekday (flight_no, weekday)
        VALUES (%s, %s)
    """


def _flight_stopover_sql() -> str:
    return """
        INSERT INTO flight_stopover (flight_no, stop_order, airport_code)
        VALUES (%s, %s, %s)
    """
