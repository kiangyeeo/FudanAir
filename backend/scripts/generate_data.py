from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from tqdm import tqdm


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.id_generator import gen_instance_id
from app.domains.flight.pricing import default_cabin_price_specs


INITIAL_INSTANCE_STATUS = "可订"
INSERT_BATCH_SIZE = 5000


def generate_flight_instances(cur: Any) -> int:
    start_date, end_date = _default_date_range()
    dates_by_weekday = _dates_by_weekday(start_date, end_date)
    seed_rows = _flight_seed_rows(cur)
    total = _total_instances(seed_rows, dates_by_weekday)
    count = 0
    params: list[tuple[Any, ...]] = []

    with tqdm(total=total, desc="生成航班实例", unit="row") as progress:
        for flight_no, weekday, economy_seats, first_seats, _, _ in seed_rows:
            flight_dates = dates_by_weekday[int(weekday)]
            for flight_date in flight_dates:
                params.append(
                    (
                        gen_instance_id(str(flight_no), flight_date),
                        flight_no,
                        flight_date,
                        int(economy_seats),
                        int(first_seats),
                        INITIAL_INSTANCE_STATUS,
                    )
                )
                count += _flush_many(cur, _insert_instance_sql(), params)
            progress.update(len(flight_dates))

    count += _flush_many(cur, _insert_instance_sql(), params, force=True)
    return count


def generate_cabin_prices(cur: Any) -> int:
    start_date, end_date = _default_date_range()
    dates_by_weekday = _dates_by_weekday(start_date, end_date)
    seed_rows = _flight_seed_rows(cur)
    total = _total_cabin_prices(seed_rows, dates_by_weekday)
    count = 0
    params: list[tuple[Any, ...]] = []

    with tqdm(total=total, desc="生成舱位定价", unit="row") as progress:
        for (
            flight_no,
            weekday,
            economy_seats,
            first_seats,
            departure,
            arrival,
        ) in seed_rows:
            specs = default_cabin_price_specs(
                int(economy_seats),
                int(first_seats),
                departure,
                arrival,
            )
            flight_dates = dates_by_weekday[int(weekday)]
            for flight_date in flight_dates:
                instance_id = gen_instance_id(str(flight_no), flight_date)
                for spec in specs:
                    params.append(
                        (
                            instance_id,
                            spec.cabin_class,
                            spec.fare_type,
                            spec.price,
                            spec.available_seats,
                        )
                    )
                    count += _flush_many(cur, _insert_cabin_price_sql(), params)
                progress.update(len(specs))

    count += _flush_many(cur, _insert_cabin_price_sql(), params, force=True)
    return count


def _default_date_range() -> tuple[date, date]:
    start_date = date.today()
    end_date = start_date + timedelta(days=settings.INSTANCE_AHEAD_DAYS)
    return start_date, end_date


def _dates_by_weekday(start_date: date, end_date: date) -> dict[int, list[date]]:
    dates = {weekday: [] for weekday in range(1, 8)}
    current = start_date
    while current <= end_date:
        dates[current.isoweekday()].append(current)
        current += timedelta(days=1)
    return dates


def _flight_seed_rows(cur: Any) -> tuple[tuple[Any, ...], ...]:
    cur.execute(
        """
        SELECT
            f.flight_no,
            fw.weekday,
            at.economy_seats,
            at.first_seats,
            f.scheduled_departure,
            f.scheduled_arrival
        FROM flight f
        JOIN flight_weekday fw ON f.flight_no = fw.flight_no
        JOIN aircraft_type at ON f.aircraft_model = at.model
        ORDER BY f.flight_no, fw.weekday
        """
    )
    return tuple(cur.fetchall())


def _total_instances(
    rows: tuple[tuple[Any, ...], ...],
    dates_by_weekday: dict[int, list[date]],
) -> int:
    return sum(len(dates_by_weekday[int(row[1])]) for row in rows)


def _total_cabin_prices(
    rows: tuple[tuple[Any, ...], ...],
    dates_by_weekday: dict[int, list[date]],
) -> int:
    total = 0
    for row in rows:
        _, weekday, economy_seats, first_seats, departure, arrival = row
        specs = default_cabin_price_specs(
            int(economy_seats),
            int(first_seats),
            departure,
            arrival,
        )
        total += len(dates_by_weekday[int(weekday)]) * len(specs)
    return total


def _flush_many(
    cur: Any,
    sql: str,
    params: list[tuple[Any, ...]],
    force: bool = False,
) -> int:
    if len(params) < INSERT_BATCH_SIZE and not force:
        return 0
    if not params:
        return 0
    cur.executemany(sql, params)
    inserted = int(cur.rowcount or 0)
    params.clear()
    return inserted


def _insert_instance_sql() -> str:
    return """
        INSERT IGNORE INTO flight_instance (
            instance_id, flight_no, flight_date,
            economy_left, first_left, status
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
