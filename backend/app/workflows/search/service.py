from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.constants import TRANSIT_MAX_MINUTES, TRANSIT_MIN_MINUTES
from app.domains.flight.service import INSTANCE_STATUS_BOOKABLE
from app.workflows.search.schemas import FlightSearchRequest, SearchSort


DIRECT_SORT_COLUMNS = {
    "price": "min_price",
    "duration": "duration_minutes",
    "departure": "scheduled_departure",
}
TRANSIT_SORT_COLUMNS = {
    "price": "total_min_price",
    "duration": "total_duration_minutes",
    "departure": "leg1_scheduled_departure",
}


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_flights(self, payload: FlightSearchRequest) -> dict[str, list[dict[str, Any]]]:
        return {
            "direct": self._search_direct(payload),
            "transit": self._search_transit(payload),
            "nearby": self._search_nearby(payload),
        }

    def search_transit(self, payload: FlightSearchRequest) -> list[dict[str, Any]]:
        return self._search_transit(payload)

    def _search_direct(self, payload: FlightSearchRequest) -> list[dict[str, Any]]:
        sql = _search_sql(
            f"""
            SELECT
                v.instance_id,
                v.flight_no,
                v.dep_airport_code,
                v.arr_airport_code,
                v.scheduled_departure,
                v.scheduled_arrival,
                v.airline_code,
                v.airline_name,
                v.aircraft_model,
                MIN(cp.price) AS min_ticket_price,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(cp.cabin_class ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                    ',',
                    1
                ) AS min_cabin_class,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(cp.fare_type ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                    ',',
                    1
                ) AS min_fare_type,
                v.fuel_infra_fee,
                MIN(cp.price + v.fuel_infra_fee) AS min_price,
                v.economy_left,
                v.first_left,
                {_duration_minutes_expr("v")} AS duration_minutes
            FROM v_flight_search v
            JOIN city_near_apt dep_rel
              ON dep_rel.iata_code = v.dep_airport_code
             AND dep_rel.city_name = :dep_city
             AND dep_rel.distance = 0
            JOIN city_near_apt arr_rel
              ON arr_rel.iata_code = v.arr_airport_code
             AND arr_rel.city_name = :arr_city
             AND arr_rel.distance = 0
            JOIN cabin_price cp ON cp.instance_id = v.instance_id
            WHERE v.flight_date = :flight_date
              AND v.instance_status = :bookable_status
              AND TIMESTAMP(v.flight_date, v.scheduled_departure) > :now
              AND cp.available_seats > 0
              AND (:airline_filter_enabled = FALSE OR v.airline_code IN :airline_codes)
              AND (:cabin_class IS NULL OR cp.cabin_class = :cabin_class)
              AND (:price_min IS NULL OR cp.price + v.fuel_infra_fee >= :price_min)
              AND (:price_max IS NULL OR cp.price + v.fuel_infra_fee <= :price_max)
              AND (:time_start IS NULL OR v.scheduled_departure >= :time_start)
              AND (:time_end IS NULL OR v.scheduled_departure <= :time_end)
              AND (
                    :include_stopover = TRUE
                 OR NOT EXISTS (
                        SELECT 1
                        FROM flight_stopover fs
                        WHERE fs.flight_no = v.flight_no
                    )
              )
            GROUP BY
                v.instance_id,
                v.flight_no,
                v.dep_airport_code,
                v.arr_airport_code,
                v.scheduled_departure,
                v.scheduled_arrival,
                v.airline_code,
                v.airline_name,
                v.aircraft_model,
                v.fuel_infra_fee,
                v.economy_left,
                v.first_left,
                v.flight_date
            {_order_by(payload.sort, DIRECT_SORT_COLUMNS)}
            """
        )
        rows = self.db.execute(sql, _query_params(payload)).mappings().all()
        return [_direct_candidate(row) for row in rows]

    def _search_transit(self, payload: FlightSearchRequest) -> list[dict[str, Any]]:
        sql = _search_sql(
            f"""
            WITH candidates AS (
                SELECT
                    v.instance_id,
                    v.flight_no,
                    v.flight_date,
                    v.dep_airport_code,
                    v.arr_airport_code,
                    v.scheduled_departure,
                    v.scheduled_arrival,
                    v.airline_code,
                    v.airline_name,
                    v.aircraft_model,
                    MIN(cp.price) AS min_ticket_price,
                    SUBSTRING_INDEX(
                        GROUP_CONCAT(cp.cabin_class ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                        ',',
                        1
                    ) AS min_cabin_class,
                    SUBSTRING_INDEX(
                        GROUP_CONCAT(cp.fare_type ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                        ',',
                        1
                    ) AS min_fare_type,
                    v.fuel_infra_fee,
                    MIN(cp.price + v.fuel_infra_fee) AS min_price,
                    v.economy_left,
                    v.first_left,
                    TIMESTAMP(v.flight_date, v.scheduled_departure) AS dep_dt,
                    {_arrival_datetime_expr("v")} AS arr_dt,
                    {_duration_minutes_expr("v")} AS duration_minutes
                FROM v_flight_search v
                JOIN cabin_price cp ON cp.instance_id = v.instance_id
                WHERE v.flight_date IN (:flight_date, DATE_ADD(:flight_date, INTERVAL 1 DAY))
                  AND v.instance_status = :bookable_status
                  AND TIMESTAMP(v.flight_date, v.scheduled_departure) > :now
                  AND cp.available_seats > 0
                  AND (:airline_filter_enabled = FALSE OR v.airline_code IN :airline_codes)
                  AND (:cabin_class IS NULL OR cp.cabin_class = :cabin_class)
                  AND (:time_start IS NULL OR v.scheduled_departure >= :time_start)
                  AND (:time_end IS NULL OR v.scheduled_departure <= :time_end)
                  AND (
                        :include_stopover = TRUE
                     OR NOT EXISTS (
                            SELECT 1
                            FROM flight_stopover fs
                            WHERE fs.flight_no = v.flight_no
                        )
                  )
                GROUP BY
                    v.instance_id,
                    v.flight_no,
                    v.flight_date,
                    v.dep_airport_code,
                    v.arr_airport_code,
                    v.scheduled_departure,
                    v.scheduled_arrival,
                    v.airline_code,
                    v.airline_name,
                    v.aircraft_model,
                    v.fuel_infra_fee,
                    v.economy_left,
                    v.first_left
            )
            SELECT
                leg1.instance_id AS leg1_instance_id,
                leg1.flight_no AS leg1_flight_no,
                leg1.dep_airport_code AS leg1_dep_airport_code,
                leg1.arr_airport_code AS leg1_arr_airport_code,
                leg1.scheduled_departure AS leg1_scheduled_departure,
                leg1.scheduled_arrival AS leg1_scheduled_arrival,
                leg1.airline_code AS leg1_airline_code,
                leg1.airline_name AS leg1_airline_name,
                leg1.aircraft_model AS leg1_aircraft_model,
                leg1.min_ticket_price AS leg1_min_ticket_price,
                leg1.min_cabin_class AS leg1_min_cabin_class,
                leg1.min_fare_type AS leg1_min_fare_type,
                leg1.fuel_infra_fee AS leg1_fuel_infra_fee,
                leg1.min_price AS leg1_min_price,
                leg1.economy_left AS leg1_economy_left,
                leg1.first_left AS leg1_first_left,
                leg2.instance_id AS leg2_instance_id,
                leg2.flight_no AS leg2_flight_no,
                leg2.dep_airport_code AS leg2_dep_airport_code,
                leg2.arr_airport_code AS leg2_arr_airport_code,
                leg2.scheduled_departure AS leg2_scheduled_departure,
                leg2.scheduled_arrival AS leg2_scheduled_arrival,
                leg2.airline_code AS leg2_airline_code,
                leg2.airline_name AS leg2_airline_name,
                leg2.aircraft_model AS leg2_aircraft_model,
                leg2.min_ticket_price AS leg2_min_ticket_price,
                leg2.min_cabin_class AS leg2_min_cabin_class,
                leg2.min_fare_type AS leg2_min_fare_type,
                leg2.fuel_infra_fee AS leg2_fuel_infra_fee,
                leg2.min_price AS leg2_min_price,
                leg2.economy_left AS leg2_economy_left,
                leg2.first_left AS leg2_first_left,
                leg1.arr_airport_code AS transit_airport,
                TIMESTAMPDIFF(MINUTE, leg1.arr_dt, leg2.dep_dt) AS transit_minutes,
                TIMESTAMPDIFF(MINUTE, leg1.dep_dt, leg2.arr_dt) AS total_duration_minutes,
                leg1.min_ticket_price + leg2.min_ticket_price AS total_ticket_price,
                leg1.fuel_infra_fee + leg2.fuel_infra_fee AS total_fuel_infra_fee,
                leg1.min_price + leg2.min_price AS total_min_price
            FROM candidates leg1
            JOIN candidates leg2
              ON leg1.arr_airport_code = leg2.dep_airport_code
             AND leg1.instance_id <> leg2.instance_id
             AND leg1.flight_date = :flight_date
             AND leg2.flight_date IN (:flight_date, DATE_ADD(:flight_date, INTERVAL 1 DAY))
             AND TIMESTAMPDIFF(MINUTE, leg1.arr_dt, leg2.dep_dt)
                 BETWEEN :min_transit_minutes AND :max_transit_minutes
            JOIN city_near_apt dep_rel
              ON dep_rel.iata_code = leg1.dep_airport_code
             AND dep_rel.city_name = :dep_city
             AND dep_rel.distance = 0
            JOIN city_near_apt arr_rel
              ON arr_rel.iata_code = leg2.arr_airport_code
             AND arr_rel.city_name = :arr_city
             AND arr_rel.distance = 0
            WHERE (:price_min IS NULL OR leg1.min_price + leg2.min_price >= :price_min)
              AND (:price_max IS NULL OR leg1.min_price + leg2.min_price <= :price_max)
            {_order_by(payload.sort, TRANSIT_SORT_COLUMNS, "leg1_scheduled_departure", "leg1_flight_no")}
            """
        )
        rows = self.db.execute(sql, _query_params(payload)).mappings().all()
        return [_transit_candidate(row) for row in rows]

    def _search_nearby(self, payload: FlightSearchRequest) -> list[dict[str, Any]]:
        common_where = """
              AND cp.available_seats > 0
              AND v.instance_status = :bookable_status
              AND TIMESTAMP(v.flight_date, v.scheduled_departure) > :now
              AND (:airline_filter_enabled = FALSE OR v.airline_code IN :airline_codes)
              AND (:cabin_class IS NULL OR cp.cabin_class = :cabin_class)
              AND (:price_min IS NULL OR cp.price + v.fuel_infra_fee >= :price_min)
              AND (:price_max IS NULL OR cp.price + v.fuel_infra_fee <= :price_max)
              AND (:time_start IS NULL OR v.scheduled_departure >= :time_start)
              AND (:time_end IS NULL OR v.scheduled_departure <= :time_end)
              AND (
                    :include_stopover = TRUE
                 OR NOT EXISTS (
                        SELECT 1
                        FROM flight_stopover fs
                        WHERE fs.flight_no = v.flight_no
                    )
              )
        """
        group_by = """
            GROUP BY
                replacement,
                replaced_airport,
                actual_dep_city,
                actual_arr_city,
                v.instance_id,
                v.flight_no,
                v.dep_airport_code,
                v.arr_airport_code,
                v.scheduled_departure,
                v.scheduled_arrival,
                v.airline_code,
                v.airline_name,
                v.aircraft_model,
                v.fuel_infra_fee,
                v.economy_left,
                v.first_left,
                v.flight_date
        """
        select_columns = f"""
                replacement,
                replaced_airport,
                actual_dep_city,
                actual_arr_city,
                v.instance_id,
                v.flight_no,
                v.dep_airport_code,
                v.arr_airport_code,
                v.scheduled_departure,
                v.scheduled_arrival,
                v.airline_code,
                v.airline_name,
                v.aircraft_model,
                MIN(cp.price) AS min_ticket_price,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(cp.cabin_class ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                    ',',
                    1
                ) AS min_cabin_class,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(cp.fare_type ORDER BY cp.price + v.fuel_infra_fee, cp.cabin_class, cp.fare_type),
                    ',',
                    1
                ) AS min_fare_type,
                v.fuel_infra_fee,
                MIN(cp.price + v.fuel_infra_fee) AS min_price,
                v.economy_left,
                v.first_left,
                {_duration_minutes_expr("v")} AS duration_minutes
        """
        sql = _search_sql(
            f"""
            SELECT {select_columns}
            FROM (
                SELECT
                    'departure' AS replacement,
                    v.dep_airport_code AS replaced_airport,
                    v.dep_city AS actual_dep_city,
                    NULL AS actual_arr_city,
                    v.instance_id,
                    v.flight_no,
                    v.flight_date,
                    v.instance_status,
                    v.scheduled_departure,
                    v.scheduled_arrival,
                    v.fuel_infra_fee,
                    v.dep_airport_code,
                    v.dep_city,
                    v.arr_airport_code,
                    v.arr_city,
                    v.airline_code,
                    v.airline_name,
                    v.aircraft_model,
                    v.economy_left,
                    v.first_left
                FROM v_flight_search v
                JOIN city_near_apt dep_near
                  ON dep_near.iata_code = v.dep_airport_code
                 AND dep_near.city_name = :dep_city
                 AND dep_near.distance > 0
                JOIN city_near_apt arr_rel
                  ON arr_rel.iata_code = v.arr_airport_code
                 AND arr_rel.city_name = :arr_city
                 AND arr_rel.distance = 0
                WHERE v.flight_date = :flight_date

                UNION ALL

                SELECT
                    'arrival' AS replacement,
                    v.arr_airport_code AS replaced_airport,
                    NULL AS actual_dep_city,
                    v.arr_city AS actual_arr_city,
                    v.instance_id,
                    v.flight_no,
                    v.flight_date,
                    v.instance_status,
                    v.scheduled_departure,
                    v.scheduled_arrival,
                    v.fuel_infra_fee,
                    v.dep_airport_code,
                    v.dep_city,
                    v.arr_airport_code,
                    v.arr_city,
                    v.airline_code,
                    v.airline_name,
                    v.aircraft_model,
                    v.economy_left,
                    v.first_left
                FROM v_flight_search v
                JOIN city_near_apt dep_rel
                  ON dep_rel.iata_code = v.dep_airport_code
                 AND dep_rel.city_name = :dep_city
                 AND dep_rel.distance = 0
                JOIN city_near_apt arr_near
                  ON arr_near.iata_code = v.arr_airport_code
                 AND arr_near.city_name = :arr_city
                 AND arr_near.distance > 0
                WHERE v.flight_date = :flight_date
            ) v
            JOIN cabin_price cp ON cp.instance_id = v.instance_id
            WHERE 1 = 1
            {common_where}
            {group_by}
            {_order_by(payload.sort, DIRECT_SORT_COLUMNS)}
            """
        )
        rows = self.db.execute(sql, _query_params(payload)).mappings().all()
        return [_nearby_candidate(row) for row in rows]


def _query_params(payload: FlightSearchRequest) -> dict[str, Any]:
    filters = payload.filters
    time_start = None
    time_end = None
    if filters.departure_time_range is not None:
        time_start, time_end = filters.departure_time_range
    airline_codes = filters.airline_codes or ([filters.airline_code] if filters.airline_code else [])
    return {
        "dep_city": payload.dep_city,
        "arr_city": payload.arr_city,
        "flight_date": payload.flight_date,
        "bookable_status": INSTANCE_STATUS_BOOKABLE,
        "now": datetime.now(),
        "airline_codes": airline_codes,
        "airline_filter_enabled": bool(airline_codes),
        "cabin_class": filters.cabin_class,
        "price_min": filters.price_min,
        "price_max": filters.price_max,
        "time_start": time_start,
        "time_end": time_end,
        "include_stopover": filters.include_stopover,
        "min_transit_minutes": TRANSIT_MIN_MINUTES,
        "max_transit_minutes": TRANSIT_MAX_MINUTES,
    }


def _search_sql(sql: str):
    return text(sql).bindparams(bindparam("airline_codes", expanding=True))


def _order_by(
    sort: SearchSort,
    allowed_columns: dict[str, str],
    departure_column: str = "scheduled_departure",
    flight_column: str = "flight_no",
) -> str:
    column = allowed_columns[sort.field]
    direction = "DESC" if sort.order == "desc" else "ASC"
    return f"ORDER BY {column} {direction}, {departure_column} ASC, {flight_column} ASC"


def _arrival_datetime_expr(alias: str) -> str:
    return f"""
        CASE
            WHEN {alias}.scheduled_arrival >= {alias}.scheduled_departure
            THEN TIMESTAMP({alias}.flight_date, {alias}.scheduled_arrival)
            ELSE TIMESTAMP(DATE_ADD({alias}.flight_date, INTERVAL 1 DAY), {alias}.scheduled_arrival)
        END
    """


def _duration_minutes_expr(alias: str) -> str:
    return f"""
        TIMESTAMPDIFF(
            MINUTE,
            TIMESTAMP({alias}.flight_date, {alias}.scheduled_departure),
            {_arrival_datetime_expr(alias)}
        )
    """


def _direct_candidate(row: Any, prefix: str = "") -> dict[str, Any]:
    data = dict(row)
    return {
        "type": "direct",
        "instance_id": data[f"{prefix}instance_id"],
        "flight_no": data[f"{prefix}flight_no"],
        "dep_airport_code": data[f"{prefix}dep_airport_code"],
        "arr_airport_code": data[f"{prefix}arr_airport_code"],
        "scheduled_departure": _normalize_time(data[f"{prefix}scheduled_departure"]),
        "scheduled_arrival": _normalize_time(data[f"{prefix}scheduled_arrival"]),
        "airline_code": data[f"{prefix}airline_code"],
        "airline_name": data[f"{prefix}airline_name"],
        "aircraft_model": data[f"{prefix}aircraft_model"],
        "min_price": _number(data[f"{prefix}min_price"]),
        "min_ticket_price": _number(data[f"{prefix}min_ticket_price"]),
        "min_cabin_class": data[f"{prefix}min_cabin_class"],
        "min_fare_type": data[f"{prefix}min_fare_type"],
        "fuel_infra_fee": _number(data[f"{prefix}fuel_infra_fee"]),
        "economy_left": int(data[f"{prefix}economy_left"]),
        "first_left": int(data[f"{prefix}first_left"]),
    }


def _nearby_candidate(row: Any) -> dict[str, Any]:
    data = dict(row)
    candidate = _direct_candidate(data)
    candidate["type"] = "nearby"
    candidate["replacement"] = data["replacement"]
    candidate["replaced_airport"] = data["replaced_airport"]
    candidate["actual_dep_city"] = data.get("actual_dep_city")
    candidate["actual_arr_city"] = data.get("actual_arr_city")
    return candidate


def _transit_candidate(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "type": "transit",
        "leg1": _direct_candidate(data, "leg1_"),
        "leg2": _direct_candidate(data, "leg2_"),
        "transit_airport": data["transit_airport"],
        "transit_minutes": int(data["transit_minutes"]),
        "total_duration_minutes": int(data["total_duration_minutes"]),
        "total_min_price": _number(data["total_min_price"]),
        "total_ticket_price": _number(data["total_ticket_price"]),
        "total_fuel_infra_fee": _number(data["total_fuel_infra_fee"]),
    }


def _normalize_time(value: Any) -> Any:
    if not isinstance(value, timedelta):
        return value
    total_seconds = int(value.total_seconds()) % (24 * 60 * 60)
    hour, remainder = divmod(total_seconds, 60 * 60)
    minute, second = divmod(remainder, 60)
    return time(hour=hour, minute=minute, second=second, microsecond=value.microseconds)


def _number(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)
