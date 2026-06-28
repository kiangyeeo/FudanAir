from __future__ import annotations

import asyncio
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.auth.dependencies import get_current_user_id
from app.config import settings
from app.core.database import SessionLocal, engine
from app.core.exceptions import AppException
from app.jobs import expire_orders as expire_orders_module
from app.workflows.booking.router import router as booking_router


REQUEST_COUNT = 8
STOCK = 3
AIRLINE_CODE = "9Z"
DEP_AIRPORT = "9ZA"
ARR_AIRPORT = "9ZB"
AIRCRAFT_MODEL = "9Z-A320"
DEP_CITY = "并发测试出发"
ARR_CITY = "并发测试到达"


@dataclass(frozen=True)
class BookingInventory:
    user_id: int
    user_phone: str
    flight_no: str
    instance_id: str
    passenger_prefix: str
    stock: int


def test_concurrent_booking_allows_only_stock_count_successes() -> None:
    _require_mysql()
    inventory = _prepare_inventory("9Z9001", STOCK)
    try:
        app = _booking_test_app(inventory.user_id)

        responses = _send_concurrent_booking_requests(app, inventory, REQUEST_COUNT)

        successes = [response for response in responses if response.status_code == 201]
        conflicts = [response for response in responses if response.status_code == 409]
        assert len(successes) == inventory.stock, _debug_responses(responses)
        assert len(conflicts) == REQUEST_COUNT - inventory.stock, _debug_responses(responses)
        assert {response.json()["code"] for response in conflicts} == {"INSUFFICIENT_STOCK"}
        assert _stock_snapshot(inventory.instance_id) == (0, 0)
        assert _ticket_count(inventory.user_id, inventory.instance_id) == inventory.stock
    finally:
        _cleanup_inventory(inventory)


def test_expire_orders_job_with_one_minute_setting_restores_stock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_mysql()
    inventory = _prepare_inventory("9Z9002", 1)
    try:
        app = _booking_test_app(inventory.user_id)
        response = asyncio.run(_post_booking(app, _booking_payload(inventory, 0)))
        assert response.status_code == 201, response.text
        order_no = response.json()["order_no"]
        assert _stock_snapshot(inventory.instance_id) == (0, 0)

        _mark_order_created_before(order_no, minutes=2)
        monkeypatch.setattr(settings, "ORDER_EXPIRE_MINUTES", 1)
        _patch_expired_order_scan(monkeypatch, order_no)

        expire_orders_module.expire_orders_job()

        assert _order_status(order_no) == "已取消"
        assert _ticket_statuses(order_no) == ["已退"]
        assert _stock_snapshot(inventory.instance_id) == (1, 1)
    finally:
        _cleanup_inventory(inventory)


def _booking_test_app(user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(booking_router, prefix="/api/booking")
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    @app.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    return app


def _send_concurrent_booking_requests(
    app: FastAPI,
    inventory: BookingInventory,
    request_count: int,
) -> list[httpx.Response]:
    barrier = threading.Barrier(request_count)
    lock = threading.Lock()
    responses: list[httpx.Response | None] = [None] * request_count
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            response = asyncio.run(_post_booking(app, _booking_payload(inventory, index)))
            responses[index] = response
        except BaseException as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(request_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    alive = [thread.name for thread in threads if thread.is_alive()]
    assert not alive, f"并发请求线程未结束: {alive}"
    assert not errors, [repr(error) for error in errors]
    return [response for response in responses if response is not None]


async def _post_booking(app: FastAPI, payload: dict[str, Any]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=20,
    ) as client:
        return await client.post("/api/booking", json=payload)


def _booking_payload(inventory: BookingInventory, index: int) -> dict[str, Any]:
    return {
        "instance_id": inventory.instance_id,
        "cabin_class": "经济舱",
        "fare_type": "标准",
        "passengers": [
            {
                "id_no": f"{inventory.passenger_prefix}{index:03d}",
                "real_name": f"并发乘机人{index}",
                "birth_date": "1990-01-01",
            }
        ],
    }


def _prepare_inventory(flight_no: str, stock: int) -> BookingInventory:
    suffix = uuid.uuid4().hex[:8]
    phone = f"199{int(suffix, 16) % 100000000:08d}"
    flight_date = date.today() + timedelta(days=30)
    instance_id = f"{flight_no}_{flight_date:%Y%m%d}"
    passenger_prefix = f"PC{suffix}"
    inventory = BookingInventory(0, phone, flight_no, instance_id, passenger_prefix, stock)

    _cleanup_inventory(inventory)
    with SessionLocal() as db:
        _insert_reference_rows(db, flight_no, flight_date)
        _insert_inventory_rows(db, inventory, flight_date)
        user_id = _insert_user(db, phone)
        db.commit()

    seeded = BookingInventory(user_id, phone, flight_no, instance_id, passenger_prefix, stock)
    _ensure_ticket_sequence_seed(seeded)
    return seeded


def _insert_reference_rows(db: Any, flight_no: str, flight_date: date) -> None:
    _insert_cities_and_airports(db)
    _insert_airline_and_aircraft(db)
    _insert_flight_schedule(db, flight_no, flight_date)


def _insert_cities_and_airports(db: Any) -> None:
    db.execute(text("INSERT INTO city (city_name) VALUES (:city)"), {"city": DEP_CITY})
    db.execute(text("INSERT INTO city (city_name) VALUES (:city)"), {"city": ARR_CITY})
    db.execute(
        text(
            """
            INSERT INTO airport (iata_code, airport_name, city_name)
            VALUES (:code, :name, :city)
            """
        ),
        {"code": DEP_AIRPORT, "name": "并发测试出发机场", "city": DEP_CITY},
    )
    db.execute(
        text(
            """
            INSERT INTO airport (iata_code, airport_name, city_name)
            VALUES (:code, :name, :city)
            """
        ),
        {"code": ARR_AIRPORT, "name": "并发测试到达机场", "city": ARR_CITY},
    )


def _insert_airline_and_aircraft(db: Any) -> None:
    db.execute(
        text("INSERT INTO airline (iata_code, airline_name) VALUES (:code, :name)"),
        {"code": AIRLINE_CODE, "name": "并发测试航空"},
    )
    db.execute(
        text(
            """
            INSERT INTO aircraft_type (model, economy_seats, first_seats)
            VALUES (:model, 200, 0)
            """
        ),
        {"model": AIRCRAFT_MODEL},
    )


def _insert_flight_schedule(db: Any, flight_no: str, flight_date: date) -> None:
    db.execute(
        text(
            """
            INSERT INTO flight
                (flight_no, scheduled_departure, scheduled_arrival, fuel_infra_fee,
                 dep_airport_code, arr_airport_code, airline_code, aircraft_model)
            VALUES
                (:flight_no, '08:00:00', '10:00:00', 50.00,
                 :dep_airport, :arr_airport, :airline, :aircraft)
            """
        ),
        {
            "flight_no": flight_no,
            "dep_airport": DEP_AIRPORT,
            "arr_airport": ARR_AIRPORT,
            "airline": AIRLINE_CODE,
            "aircraft": AIRCRAFT_MODEL,
        },
    )
    db.execute(
        text("INSERT INTO flight_weekday (flight_no, weekday) VALUES (:flight_no, :weekday)"),
        {"flight_no": flight_no, "weekday": flight_date.isoweekday()},
    )


def _insert_inventory_rows(
    db: Any,
    inventory: BookingInventory,
    flight_date: date,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO flight_instance
                (instance_id, flight_no, flight_date, scheduled_departure, scheduled_arrival, fuel_infra_fee, economy_left, first_left, status)
            VALUES
                (:instance_id, :flight_no, :flight_date, '08:00:00', '10:00:00', 50.00, :stock, 0, '可订')
            """
        ),
        {
            "instance_id": inventory.instance_id,
            "flight_no": inventory.flight_no,
            "flight_date": flight_date,
            "stock": inventory.stock,
        },
    )
    db.execute(
        text(
            """
            INSERT INTO cabin_price
                (instance_id, cabin_class, fare_type, price, available_seats)
            VALUES
                (:instance_id, '经济舱', '标准', 100.00, :stock)
            """
        ),
        {"instance_id": inventory.instance_id, "stock": inventory.stock},
    )


def _insert_user(db: Any, phone: str) -> int:
    db.execute(
        text(
            """
            INSERT INTO `user` (user_password, name, phone)
            VALUES ('test-password', '并发测试用户', :phone)
            """
        ),
        {"phone": phone},
    )
    return int(db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one())


def _ensure_ticket_sequence_seed(inventory: BookingInventory) -> None:
    prefix = f"T{date.today():%Y%m%d}"
    with SessionLocal() as db:
        has_today_ticket = db.execute(
            text("SELECT 1 FROM ticket WHERE ticket_no LIKE :prefix LIMIT 1"),
            {"prefix": f"{prefix}%"},
        ).first()
        if has_today_ticket:
            return
        seed_order_no = f"OSEED{inventory.passenger_prefix}"
        seed_passenger_id = f"{inventory.passenger_prefix}SEED"
        db.execute(
            text(
                """
                INSERT INTO passenger (id_no, real_name, birth_date)
                VALUES (:id_no, '并发种子乘机人', '1990-01-01')
                """
            ),
            {"id_no": seed_passenger_id},
        )
        db.execute(
            text(
                """
                INSERT INTO aptorder (order_no, user_id, total_amount, status, created_at)
                VALUES (:order_no, :user_id, 0.00, '已取消', NOW())
                """
            ),
            {"order_no": seed_order_no, "user_id": inventory.user_id},
        )
        db.execute(
            text(
                """
                INSERT INTO ticket
                    (ticket_no, order_no, passenger_id, instance_id,
                     cabin_class, fare_type, actual_price, status)
                VALUES
                    (:ticket_no, :order_no, :passenger_id, :instance_id,
                     '经济舱', '标准', 0.00, '已退')
                """
            ),
            {
                "ticket_no": f"{prefix}000000000",
                "order_no": seed_order_no,
                "passenger_id": seed_passenger_id,
                "instance_id": inventory.instance_id,
            },
        )
        db.commit()


def _patch_expired_order_scan(
    monkeypatch: pytest.MonkeyPatch,
    order_no: str,
) -> None:
    class TestOrderRepository(expire_orders_module.OrderRepository):
        def list_expired_pending_order_nos(self, expire_before: Any) -> list[str]:
            row = self.db.execute(
                text(
                    """
                    SELECT order_no
                    FROM aptorder
                    WHERE order_no = :order_no
                      AND status = '待支付'
                      AND created_at < :expire_before
                    """
                ),
                {"order_no": order_no, "expire_before": expire_before},
            ).scalar_one_or_none()
            return [str(row)] if row else []

    monkeypatch.setattr(expire_orders_module, "OrderRepository", TestOrderRepository)


def _mark_order_created_before(order_no: str, minutes: int) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE aptorder
                SET created_at = NOW() - INTERVAL :minutes MINUTE
                WHERE order_no = :order_no
                """
            ),
            {"order_no": order_no, "minutes": minutes},
        )
        db.commit()


def _stock_snapshot(instance_id: str) -> tuple[int, int]:
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT cp.available_seats, fi.economy_left
                FROM cabin_price cp
                JOIN flight_instance fi ON cp.instance_id = fi.instance_id
                WHERE cp.instance_id = :instance_id
                  AND cp.cabin_class = '经济舱'
                  AND cp.fare_type = '标准'
                """
            ),
            {"instance_id": instance_id},
        ).one()
    return int(row.available_seats), int(row.economy_left)


def _ticket_count(user_id: int, instance_id: str) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM ticket t
                    JOIN aptorder o ON t.order_no = o.order_no
                    WHERE o.user_id = :user_id
                      AND t.instance_id = :instance_id
                      AND t.status = '有效'
                    """
                ),
                {"user_id": user_id, "instance_id": instance_id},
            ).scalar_one()
        )


def _order_status(order_no: str) -> str:
    with SessionLocal() as db:
        return str(
            db.execute(
                text("SELECT status FROM aptorder WHERE order_no = :order_no"),
                {"order_no": order_no},
            ).scalar_one()
        )


def _ticket_statuses(order_no: str) -> list[str]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT status
                FROM ticket
                WHERE order_no = :order_no
                ORDER BY ticket_no
                """
            ),
            {"order_no": order_no},
        ).scalars().all()
    return [str(row) for row in rows]


def _cleanup_inventory(inventory: BookingInventory) -> None:
    with SessionLocal() as db:
        _delete_refund_records(db, inventory)
        _delete_tickets_and_orders(db, inventory)
        _delete_passengers_and_user(db, inventory)
        _delete_flight_inventory(db, inventory)
        _delete_reference_rows(db)
        db.commit()


def _delete_refund_records(db: Any, inventory: BookingInventory) -> None:
    db.execute(
        text(
            """
            DELETE rc
            FROM refund_change rc
            JOIN ticket t ON rc.ticket_no = t.ticket_no
            LEFT JOIN aptorder o ON t.order_no = o.order_no
            LEFT JOIN `user` u ON o.user_id = u.user_id
            WHERE u.phone = :phone OR t.instance_id = :instance_id
            """
        ),
        {"phone": inventory.user_phone, "instance_id": inventory.instance_id},
    )


def _delete_tickets_and_orders(db: Any, inventory: BookingInventory) -> None:
    order_nos = db.execute(
        text("SELECT DISTINCT order_no FROM ticket WHERE instance_id = :instance_id"),
        {"instance_id": inventory.instance_id},
    ).scalars().all()
    user_ids = db.execute(
        text("SELECT user_id FROM `user` WHERE phone = :phone"),
        {"phone": inventory.user_phone},
    ).scalars().all()
    for user_id in user_ids:
        db.execute(
            text(
                """
                DELETE FROM ticket
                WHERE order_no IN (
                    SELECT order_no FROM aptorder WHERE user_id = :user_id
                )
                """
            ),
            {"user_id": user_id},
        )
        db.execute(text("DELETE FROM aptorder WHERE user_id = :user_id"), {"user_id": user_id})
    db.execute(
        text("DELETE FROM ticket WHERE instance_id = :instance_id"),
        {"instance_id": inventory.instance_id},
    )
    for order_no in order_nos:
        db.execute(
            text(
                """
                DELETE FROM aptorder
                WHERE order_no = :order_no
                  AND NOT EXISTS (
                      SELECT 1 FROM ticket WHERE ticket.order_no = aptorder.order_no
                  )
                """
            ),
            {"order_no": order_no},
        )


def _delete_passengers_and_user(db: Any, inventory: BookingInventory) -> None:
    db.execute(
        text("DELETE FROM passenger WHERE id_no LIKE :prefix"),
        {"prefix": f"{inventory.passenger_prefix}%"},
    )
    db.execute(text("DELETE FROM `user` WHERE phone = :phone"), {"phone": inventory.user_phone})


def _delete_flight_inventory(db: Any, inventory: BookingInventory) -> None:
    db.execute(
        text("DELETE FROM cabin_price WHERE instance_id = :instance_id"),
        {"instance_id": inventory.instance_id},
    )
    db.execute(
        text("DELETE FROM flight_instance WHERE instance_id = :instance_id"),
        {"instance_id": inventory.instance_id},
    )
    db.execute(
        text("DELETE FROM flight_weekday WHERE flight_no = :flight_no"),
        {"flight_no": inventory.flight_no},
    )
    db.execute(
        text("DELETE FROM flight_stopover WHERE flight_no = :flight_no"),
        {"flight_no": inventory.flight_no},
    )
    db.execute(text("DELETE FROM flight WHERE flight_no = :flight_no"), {"flight_no": inventory.flight_no})


def _delete_reference_rows(db: Any) -> None:
    db.execute(text("DELETE FROM aircraft_type WHERE model = :model"), {"model": AIRCRAFT_MODEL})
    db.execute(text("DELETE FROM airline WHERE iata_code = :code"), {"code": AIRLINE_CODE})
    db.execute(text("DELETE FROM airport WHERE iata_code = :code"), {"code": DEP_AIRPORT})
    db.execute(text("DELETE FROM airport WHERE iata_code = :code"), {"code": ARR_AIRPORT})
    db.execute(text("DELETE FROM city WHERE city_name = :city"), {"city": DEP_CITY})
    db.execute(text("DELETE FROM city WHERE city_name = :city"), {"city": ARR_CITY})


def _require_mysql() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.skip(f"MySQL 测试库不可用: {exc}")


def _debug_responses(responses: list[httpx.Response]) -> list[tuple[int, str]]:
    return [(response.status_code, response.text) for response in responses]
