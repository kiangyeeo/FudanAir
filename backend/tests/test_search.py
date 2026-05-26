from __future__ import annotations

import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.constants import TRANSIT_MAX_MINUTES, TRANSIT_MIN_MINUTES
from app.deps import get_db
from app.workflows.search.router import router
from app.workflows.search.schemas import FlightSearchRequest
from app.workflows.search.service import SearchService


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeSession:
    def __init__(self, rows_by_call: list[list[dict[str, Any]]]):
        self.rows_by_call = rows_by_call
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any]) -> FakeResult:
        self.calls.append((str(statement), params))
        return FakeResult(self.rows_by_call.pop(0))


def test_direct_search_uses_zero_distance_airports_and_min_price_with_fee() -> None:
    db = FakeSession(
        [
            [
                {
                    "instance_id": "MU1001_20260510",
                    "flight_no": "MU1001",
                    "dep_airport_code": "SHA",
                    "arr_airport_code": "PEK",
                    "scheduled_departure": time(8, 0),
                    "scheduled_arrival": time(10, 20),
                    "airline_code": "MU",
                    "airline_name": "中国东方航空",
                    "min_ticket_price": Decimal("800.00"),
                    "fuel_infra_fee": Decimal("50.00"),
                    "min_price": Decimal("850.00"),
                    "economy_left": 12,
                    "first_left": 2,
                }
            ]
        ]
    )
    payload = FlightSearchRequest.model_validate(
        {
            "dep_city": "上海",
            "arr_city": "北京",
            "flight_date": "2026-05-10",
            "filters": {
                "airline_code": "mu",
                "cabin_class": "经济舱",
                "departure_time_range": ["07:00:00", "12:00:00"],
                "include_stopover": False,
            },
            "sort": {"field": "price", "order": "asc"},
        }
    )

    rows = SearchService(db)._search_direct(payload)

    sql, params = db.calls[0]
    assert "FROM v_flight_search v" in sql
    assert "JOIN city_near_apt dep_rel" in sql
    assert "JOIN city_near_apt arr_rel" in sql
    assert "dep_rel.distance = 0" in sql
    assert "arr_rel.distance = 0" in sql
    assert "MIN(cp.price) AS min_ticket_price" in sql
    assert "MIN(cp.price + v.fuel_infra_fee) AS min_price" in sql
    assert "v.instance_status = :bookable_status" in sql
    assert "TIMESTAMP(v.flight_date, v.scheduled_departure) > :now" in sql
    assert "cp.available_seats > 0" in sql
    assert "NOT EXISTS" in sql
    assert params["airline_codes"] == ["MU"]
    assert params["airline_filter_enabled"] is True
    assert params["cabin_class"] == "经济舱"
    assert params["include_stopover"] is False
    assert params["bookable_status"] == "可订"
    assert params["now"] is not None
    assert rows[0]["type"] == "direct"
    assert rows[0]["min_price"] == 850.0


def test_transit_search_binds_transit_window_and_builds_response_shape() -> None:
    db = FakeSession(
        [
            [
                {
                    "leg1_instance_id": "CA1001_20260510",
                    "leg1_flight_no": "CA1001",
                    "leg1_dep_airport_code": "SHA",
                    "leg1_arr_airport_code": "XIY",
                    "leg1_scheduled_departure": time(8, 0),
                    "leg1_scheduled_arrival": time(10, 0),
                    "leg1_airline_code": "CA",
                    "leg1_airline_name": "中国国际航空",
                    "leg1_min_ticket_price": Decimal("450.00"),
                    "leg1_fuel_infra_fee": Decimal("50.00"),
                    "leg1_min_price": Decimal("500.00"),
                    "leg1_economy_left": 10,
                    "leg1_first_left": 1,
                    "leg2_instance_id": "MU2001_20260510",
                    "leg2_flight_no": "MU2001",
                    "leg2_dep_airport_code": "XIY",
                    "leg2_arr_airport_code": "PEK",
                    "leg2_scheduled_departure": time(13, 0),
                    "leg2_scheduled_arrival": time(15, 0),
                    "leg2_airline_code": "MU",
                    "leg2_airline_name": "中国东方航空",
                    "leg2_min_ticket_price": Decimal("640.00"),
                    "leg2_fuel_infra_fee": Decimal("60.00"),
                    "leg2_min_price": Decimal("700.00"),
                    "leg2_economy_left": 9,
                    "leg2_first_left": 1,
                    "transit_airport": "XIY",
                    "transit_minutes": 180,
                    "total_duration_minutes": 420,
                    "total_ticket_price": Decimal("1090.00"),
                    "total_fuel_infra_fee": Decimal("110.00"),
                    "total_min_price": Decimal("1200.00"),
                }
            ]
        ]
    )
    payload = FlightSearchRequest(
        dep_city="上海",
        arr_city="北京",
        flight_date=date(2026, 5, 10),
        filters={"airline_codes": ["ca", "mu"]},
        sort={"field": "duration", "order": "asc"},
    )

    rows = SearchService(db).search_transit(payload)

    sql, params = db.calls[0]
    assert "WITH candidates AS" in sql
    assert "leg1.arr_airport_code = leg2.dep_airport_code" in sql
    assert "leg1.airline_code = leg2.airline_code" not in sql
    assert "v.airline_code IN" in sql
    assert "v.instance_status = :bookable_status" in sql
    assert "TIMESTAMP(v.flight_date, v.scheduled_departure) > :now" in sql
    assert "BETWEEN :min_transit_minutes AND :max_transit_minutes" in sql
    assert params["airline_codes"] == ["CA", "MU"]
    assert params["airline_filter_enabled"] is True
    assert params["min_transit_minutes"] == TRANSIT_MIN_MINUTES
    assert params["max_transit_minutes"] == TRANSIT_MAX_MINUTES
    assert rows[0]["type"] == "transit"
    assert rows[0]["leg1"]["type"] == "direct"
    assert rows[0]["leg1"]["airline_code"] == "CA"
    assert rows[0]["leg2"]["airline_code"] == "MU"
    assert rows[0]["leg2"]["dep_airport_code"] == "XIY"
    assert rows[0]["transit_minutes"] == 180
    assert rows[0]["total_min_price"] == 1200.0
    assert rows[0]["total_ticket_price"] == 1090.0


def test_price_range_filters_displayed_direct_and_transit_prices() -> None:
    payload = FlightSearchRequest.model_validate(
        {
            "dep_city": "上海",
            "arr_city": "北京",
            "flight_date": "2026-05-10",
            "filters": {"price_min": 800, "price_max": 1200},
        }
    )
    direct_db = FakeSession([[]])
    transit_db = FakeSession([[]])

    SearchService(direct_db)._search_direct(payload)
    SearchService(transit_db)._search_transit(payload)

    direct_sql, direct_params = direct_db.calls[0]
    transit_sql, transit_params = transit_db.calls[0]
    assert "cp.price + v.fuel_infra_fee >= :price_min" in direct_sql
    assert "cp.price + v.fuel_infra_fee <= :price_max" in direct_sql
    assert "leg1.min_price + leg2.min_price >= :price_min" in transit_sql
    assert "leg1.min_price + leg2.min_price <= :price_max" in transit_sql
    assert str(direct_params["price_min"]) == "800"
    assert str(direct_params["price_max"]) == "1200"
    assert transit_params["price_min"] == direct_params["price_min"]
    assert transit_params["price_max"] == direct_params["price_max"]


def test_nearby_search_always_uses_positive_distance_replacements() -> None:
    db = FakeSession(
        [
            [
                {
                    "replacement": "departure",
                    "replaced_airport": "SHA",
                    "actual_dep_city": "上海",
                    "actual_arr_city": None,
                    "instance_id": "HO1001_20260510",
                    "flight_no": "HO1001",
                    "dep_airport_code": "SHA",
                    "arr_airport_code": "PEK",
                    "scheduled_departure": time(9, 0),
                    "scheduled_arrival": time(11, 10),
                    "airline_code": "HO",
                    "airline_name": "吉祥航空",
                    "min_ticket_price": Decimal("730.00"),
                    "fuel_infra_fee": Decimal("50.00"),
                    "min_price": Decimal("780.00"),
                    "economy_left": 8,
                    "first_left": 0,
                }
            ]
        ]
    )
    payload = FlightSearchRequest(
        dep_city="苏州",
        arr_city="北京",
        flight_date=date(2026, 5, 10),
    )

    rows = SearchService(db)._search_nearby(payload)

    sql, _params = db.calls[0]
    assert "dep_near.distance > 0" in sql
    assert "arr_near.distance > 0" in sql
    assert "v.instance_status = :bookable_status" in sql
    assert "TIMESTAMP(v.flight_date, v.scheduled_departure) > :now" in sql
    assert "UNION ALL" in sql
    assert rows[0]["type"] == "nearby"
    assert rows[0]["replacement"] == "departure"
    assert rows[0]["replaced_airport"] == "SHA"
    assert rows[0]["actual_dep_city"] == "上海"


def test_search_flights_endpoint_returns_frontend_contract_shape() -> None:
    db = FakeSession(
        [
            [
                {
                    "instance_id": "MU1001_20260510",
                    "flight_no": "MU1001",
                    "dep_airport_code": "SHA",
                    "arr_airport_code": "PEK",
                    "scheduled_departure": time(8, 0),
                    "scheduled_arrival": time(10, 20),
                    "airline_code": "MU",
                    "airline_name": "中国东方航空",
                    "min_ticket_price": Decimal("800.00"),
                    "fuel_infra_fee": Decimal("50.00"),
                    "min_price": Decimal("850.00"),
                    "economy_left": 12,
                    "first_left": 2,
                }
            ],
            [],
            [],
        ]
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/search")

    def override_db() -> FakeSession:
        return db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(
        "/api/search/flights",
        json={
            "dep_city": "上海",
            "arr_city": "北京",
            "flight_date": "2026-05-10",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"direct", "transit", "nearby"}
    assert data["direct"][0]["type"] == "direct"
    assert data["direct"][0]["scheduled_departure"] == "08:00:00"
    assert data["transit"] == []
    assert data["nearby"] == []
