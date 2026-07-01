from __future__ import annotations

import argparse
import asyncio
import sys
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.auth.dependencies import get_current_user_id
from app.core.database import SessionLocal, engine
from app.core.exceptions import AppException
from app.workflows.booking.router import router as booking_router


DEFAULT_REQUEST_COUNT = 8
DEFAULT_STOCK = 1
DEMO_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"


@dataclass(frozen=True)
class DemoInventory:
    user_id: int
    user_phone: str
    flight_no: str
    instance_id: str
    passenger_prefix: str
    stock: int
    airline_code: str
    dep_airport: str
    arr_airport: str
    aircraft_model: str
    dep_city: str
    arr_city: str


@dataclass(frozen=True)
class DemoResult:
    success_order_nos: list[str]
    stock_failures: int
    other_responses: list[str]


def main() -> int:
    args = _parse_args()
    try:
        _require_mysql()
        inventory = _prepare_inventory(args.stock)
        return _run_demo(args.requests, inventory, args.keep_data)
    except RuntimeError as exc:
        print(f"演示失败: {exc}")
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="并发抢票演示：验证库存行锁与防超卖")
    parser.add_argument("--requests", type=int, default=DEFAULT_REQUEST_COUNT, help="并发请求数")
    parser.add_argument("--stock", type=int, default=DEFAULT_STOCK, help="初始座位库存")
    parser.add_argument("--keep-data", action="store_true", help="演示结束后保留临时数据")
    args = parser.parse_args()
    if args.stock < 1:
        parser.error("--stock 必须大于等于 1")
    if args.requests <= args.stock:
        parser.error("--requests 必须大于 --stock，才能演示抢票失败")
    return args


def _run_demo(request_count: int, inventory: DemoInventory, keep_data: bool) -> int:
    try:
        before = _stock_snapshot(inventory.instance_id)
        app = _booking_demo_app(inventory.user_id)
        responses = _send_concurrent_booking_requests(app, inventory, request_count)
        result = _summarize_responses(responses)
        after = _stock_snapshot(inventory.instance_id)
        ticket_count = _ticket_count(inventory.user_id, inventory.instance_id)
        ok = _print_report(request_count, inventory, before, after, ticket_count, result)
        return 0 if ok else 2
    finally:
        if keep_data:
            print(f"临时数据已保留，航班实例: {inventory.instance_id}")
        else:
            _cleanup_inventory(inventory)


def _require_mysql() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(f"MySQL 测试库不可用: {exc}") from exc


def _prepare_inventory(stock: int) -> DemoInventory:
    suffix = uuid.uuid4().hex[:8]
    flight_date = date.today() + timedelta(days=30)
    inventory = _new_inventory(suffix, flight_date, stock)
    _cleanup_inventory(inventory)
    with SessionLocal() as db:
        _insert_reference_rows(db, inventory, flight_date)
        _insert_inventory_rows(db, inventory, flight_date)
        user_id = _insert_user(db, inventory.user_phone)
        db.commit()
    seeded = replace(inventory, user_id=user_id)
    _ensure_ticket_sequence_seed(seeded)
    return seeded


def _new_inventory(suffix: str, flight_date: date, stock: int) -> DemoInventory:
    code_seed = int(suffix, 16)
    airline_code = "Y" + _letter_code(code_seed, 1)
    flight_no = f"{airline_code}{code_seed % 10000:04d}"
    passenger_prefix = f"DM{suffix}"
    return DemoInventory(
        user_id=0,
        user_phone=f"199{code_seed % 100000000:08d}",
        flight_no=flight_no,
        instance_id=f"{flight_no}_{flight_date:%Y%m%d}",
        passenger_prefix=passenger_prefix,
        stock=stock,
        airline_code=airline_code,
        dep_airport=_letter_code(code_seed, 2) + "A",
        arr_airport=_letter_code(code_seed + 1, 2) + "B",
        aircraft_model=f"{airline_code}-A320",
        dep_city=f"并发演示出发{suffix[:4]}",
        arr_city=f"并发演示到达{suffix[:4]}",
    )


def _letter_code(seed: int, length: int) -> str:
    base = len(DEMO_ALPHABET)
    return "".join(DEMO_ALPHABET[(seed // (base**idx)) % base] for idx in range(length))


def _booking_demo_app(user_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(booking_router, prefix="/api/booking")
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

    return app


def _send_concurrent_booking_requests(
    app: FastAPI,
    inventory: DemoInventory,
    request_count: int,
) -> list[httpx.Response]:
    barrier = threading.Barrier(request_count)
    responses: list[httpx.Response | None] = [None] * request_count
    errors: list[BaseException] = []
    lock = threading.Lock()
    threads = [_booking_thread(index, barrier, app, inventory, responses, errors, lock) for index in range(request_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    _raise_thread_errors(threads, errors)
    return [response for response in responses if response is not None]


def _booking_thread(
    index: int,
    barrier: threading.Barrier,
    app: FastAPI,
    inventory: DemoInventory,
    responses: list[httpx.Response | None],
    errors: list[BaseException],
    lock: threading.Lock,
) -> threading.Thread:
    def worker() -> None:
        try:
            barrier.wait(timeout=10)
            responses[index] = asyncio.run(_post_booking(app, _booking_payload(inventory, index)))
        except BaseException as exc:
            with lock:
                errors.append(exc)

    return threading.Thread(target=worker, name=f"booking-demo-{index}")


def _raise_thread_errors(threads: list[threading.Thread], errors: list[BaseException]) -> None:
    alive = [thread.name for thread in threads if thread.is_alive()]
    if alive:
        raise RuntimeError(f"并发请求线程未结束: {alive}")
    if errors:
        details = ", ".join(repr(error) for error in errors)
        raise RuntimeError(f"并发请求异常: {details}")


async def _post_booking(app: FastAPI, payload: dict[str, Any]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=20) as client:
        return await client.post("/api/booking", json=payload)


def _booking_payload(inventory: DemoInventory, index: int) -> dict[str, Any]:
    return {
        "instance_id": inventory.instance_id,
        "cabin_class": "经济舱",
        "fare_type": "标准",
        "passengers": [
            {
                "id_no": f"{inventory.passenger_prefix}{index:03d}",
                "real_name": f"演示乘机人{index}",
                "birth_date": "1990-01-01",
            }
        ],
    }


def _summarize_responses(responses: list[httpx.Response]) -> DemoResult:
    success_order_nos: list[str] = []
    stock_failures = 0
    other_responses: list[str] = []
    for response in responses:
        payload = _safe_json(response)
        if response.status_code == 201:
            success_order_nos.append(str(payload.get("order_no", "")))
        elif response.status_code == 409 and payload.get("code") == "INSUFFICIENT_STOCK":
            stock_failures += 1
        else:
            other_responses.append(f"{response.status_code}: {response.text}")
    return DemoResult(success_order_nos, stock_failures, other_responses)


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _print_report(
    request_count: int,
    inventory: DemoInventory,
    before: tuple[int, int],
    after: tuple[int, int],
    ticket_count: int,
    result: DemoResult,
) -> bool:
    ok = _demo_passed(request_count, inventory, after, ticket_count, result)
    print("=== FudanAir 并发抢票演示 ===")
    print(f"航班实例: {inventory.instance_id}")
    print(f"并发请求数: {request_count}")
    print(f"初始经济舱库存: {before[0]} / {before[1]} (cabin_price / flight_instance)")
    print(f"下单成功: {len(result.success_order_nos)}")
    print(f"库存不足失败: {result.stock_failures}")
    print(f"其他响应: {len(result.other_responses)}")
    print(f"最终经济舱库存: {after[0]} / {after[1]} (cabin_price / flight_instance)")
    print(f"有效客票数: {ticket_count}")
    _print_response_details(result)
    print(f"结果: {'未超卖，测试通过' if ok else '结果不符合预期，请检查响应'}")
    return ok


def _demo_passed(
    request_count: int,
    inventory: DemoInventory,
    after: tuple[int, int],
    ticket_count: int,
    result: DemoResult,
) -> bool:
    return (
        len(result.success_order_nos) == inventory.stock
        and result.stock_failures == request_count - inventory.stock
        and not result.other_responses
        and after == (0, 0)
        and ticket_count == inventory.stock
    )


def _print_response_details(result: DemoResult) -> None:
    if result.success_order_nos:
        print("成功订单: " + ", ".join(result.success_order_nos))
    if result.other_responses:
        print("异常响应:")
        for item in result.other_responses:
            print(f"- {item}")


def _insert_reference_rows(db: Any, inventory: DemoInventory, flight_date: date) -> None:
    _insert_cities_and_airports(db, inventory)
    _insert_airline_and_aircraft(db, inventory)
    _insert_flight_schedule(db, inventory, flight_date)


def _insert_cities_and_airports(db: Any, inventory: DemoInventory) -> None:
    for city in (inventory.dep_city, inventory.arr_city):
        db.execute(text("INSERT INTO city (city_name) VALUES (:city)"), {"city": city})
    _insert_airport(db, inventory.dep_airport, "并发演示出发机场", inventory.dep_city)
    _insert_airport(db, inventory.arr_airport, "并发演示到达机场", inventory.arr_city)
    _insert_near_airport(db, inventory.dep_city, inventory.dep_airport)
    _insert_near_airport(db, inventory.arr_city, inventory.arr_airport)


def _insert_airport(db: Any, code: str, name: str, city: str) -> None:
    db.execute(
        text("INSERT INTO airport (iata_code, airport_name, city_name) VALUES (:code, :name, :city)"),
        {"code": code, "name": name, "city": city},
    )


def _insert_near_airport(db: Any, city: str, code: str) -> None:
    db.execute(
        text("INSERT INTO city_near_apt (city_name, iata_code, distance) VALUES (:city, :code, 0)"),
        {"city": city, "code": code},
    )


def _insert_airline_and_aircraft(db: Any, inventory: DemoInventory) -> None:
    db.execute(
        text("INSERT INTO airline (iata_code, airline_name) VALUES (:code, :name)"),
        {"code": inventory.airline_code, "name": f"并发演示航空{inventory.airline_code}"},
    )
    db.execute(
        text("INSERT INTO aircraft_type (model, economy_seats, first_seats) VALUES (:model, 200, 0)"),
        {"model": inventory.aircraft_model},
    )


def _insert_flight_schedule(db: Any, inventory: DemoInventory, flight_date: date) -> None:
    db.execute(
        text(
            """
            INSERT INTO flight
                (flight_no, scheduled_departure, scheduled_arrival, fuel_infra_fee,
                 base_price, dep_airport_code, arr_airport_code, airline_code, aircraft_model)
            VALUES
                (:flight_no, '08:00:00', '10:00:00', 50.00,
                 100.00, :dep_airport, :arr_airport, :airline, :aircraft)
            """
        ),
        _flight_params(inventory),
    )
    db.execute(
        text("INSERT INTO flight_weekday (flight_no, weekday) VALUES (:flight_no, :weekday)"),
        {"flight_no": inventory.flight_no, "weekday": flight_date.isoweekday()},
    )


def _flight_params(inventory: DemoInventory) -> dict[str, str]:
    return {
        "flight_no": inventory.flight_no,
        "dep_airport": inventory.dep_airport,
        "arr_airport": inventory.arr_airport,
        "airline": inventory.airline_code,
        "aircraft": inventory.aircraft_model,
    }


def _insert_inventory_rows(db: Any, inventory: DemoInventory, flight_date: date) -> None:
    db.execute(
        text(
            """
            INSERT INTO flight_instance
                (instance_id, flight_no, flight_date, scheduled_departure, scheduled_arrival,
                 fuel_infra_fee, economy_left, first_left, status)
            VALUES
                (:instance_id, :flight_no, :flight_date, '08:00:00', '10:00:00',
                 50.00, :stock, 0, '可订')
            """
        ),
        _inventory_params(inventory, flight_date),
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


def _inventory_params(inventory: DemoInventory, flight_date: date) -> dict[str, object]:
    return {
        "instance_id": inventory.instance_id,
        "flight_no": inventory.flight_no,
        "flight_date": flight_date,
        "stock": inventory.stock,
    }


def _insert_user(db: Any, phone: str) -> int:
    db.execute(
        text("INSERT INTO `user` (user_password, name, phone) VALUES ('demo-password', '并发演示用户', :phone)"),
        {"phone": phone},
    )
    return int(db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one())


def _ensure_ticket_sequence_seed(inventory: DemoInventory) -> None:
    prefix = f"T{date.today():%Y%m%d}"
    with SessionLocal() as db:
        has_ticket = db.execute(text("SELECT 1 FROM ticket WHERE ticket_no LIKE :prefix LIMIT 1"), {"prefix": f"{prefix}%"}).first()
        if has_ticket:
            return
        _insert_seed_ticket(db, inventory, f"{prefix}000000000")
        db.commit()


def _insert_seed_ticket(db: Any, inventory: DemoInventory, ticket_no: str) -> None:
    seed_order_no = f"OSEED{inventory.passenger_prefix}"
    seed_passenger_id = f"{inventory.passenger_prefix}SEED"
    db.execute(text("INSERT INTO passenger (id_no, real_name, birth_date) VALUES (:id_no, '并发种子乘机人', '1990-01-01')"), {"id_no": seed_passenger_id})
    db.execute(text("INSERT INTO aptorder (order_no, user_id, total_amount, status, created_at) VALUES (:order_no, :user_id, 0.00, '已取消', NOW())"), {"order_no": seed_order_no, "user_id": inventory.user_id})
    db.execute(
        text(
            """
            INSERT INTO ticket
                (ticket_no, order_no, passenger_id, instance_id,
                 cabin_class, fare_type, actual_price, fuel_infra_fee, status)
            VALUES
                (:ticket_no, :order_no, :passenger_id, :instance_id,
                 '经济舱', '标准', 0.00, 0.00, '已退')
            """
        ),
        {"ticket_no": ticket_no, "order_no": seed_order_no, "passenger_id": seed_passenger_id, "instance_id": inventory.instance_id},
    )


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
        count = db.execute(
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
    return int(count)


def _cleanup_inventory(inventory: DemoInventory) -> None:
    with SessionLocal() as db:
        _delete_refund_records(db, inventory)
        _delete_tickets_and_orders(db, inventory)
        _delete_passengers_and_user(db, inventory)
        _delete_flight_inventory(db, inventory)
        _delete_reference_rows(db, inventory)
        db.commit()


def _delete_refund_records(db: Any, inventory: DemoInventory) -> None:
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


def _delete_tickets_and_orders(db: Any, inventory: DemoInventory) -> None:
    order_nos = _order_nos_for_inventory(db, inventory)
    db.execute(text("DELETE FROM ticket WHERE instance_id = :instance_id"), {"instance_id": inventory.instance_id})
    for order_no in order_nos:
        db.execute(text("DELETE FROM aptorder WHERE order_no = :order_no"), {"order_no": order_no})


def _order_nos_for_inventory(db: Any, inventory: DemoInventory) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT t.order_no
            FROM ticket t
            LEFT JOIN aptorder o ON t.order_no = o.order_no
            LEFT JOIN `user` u ON o.user_id = u.user_id
            WHERE t.instance_id = :instance_id OR u.phone = :phone
            """
        ),
        {"instance_id": inventory.instance_id, "phone": inventory.user_phone},
    ).scalars().all()
    return [str(row) for row in rows]


def _delete_passengers_and_user(db: Any, inventory: DemoInventory) -> None:
    db.execute(text("DELETE FROM passenger WHERE id_no LIKE :prefix"), {"prefix": f"{inventory.passenger_prefix}%"})
    db.execute(text("DELETE FROM `user` WHERE phone = :phone"), {"phone": inventory.user_phone})


def _delete_flight_inventory(db: Any, inventory: DemoInventory) -> None:
    db.execute(text("DELETE FROM cabin_price WHERE instance_id = :instance_id"), {"instance_id": inventory.instance_id})
    db.execute(text("DELETE FROM flight_instance WHERE instance_id = :instance_id"), {"instance_id": inventory.instance_id})
    db.execute(text("DELETE FROM flight_weekday WHERE flight_no = :flight_no"), {"flight_no": inventory.flight_no})
    db.execute(text("DELETE FROM flight_stopover WHERE flight_no = :flight_no"), {"flight_no": inventory.flight_no})
    db.execute(text("DELETE FROM flight WHERE flight_no = :flight_no"), {"flight_no": inventory.flight_no})


def _delete_reference_rows(db: Any, inventory: DemoInventory) -> None:
    db.execute(text("DELETE FROM aircraft_type WHERE model = :model"), {"model": inventory.aircraft_model})
    db.execute(text("DELETE FROM airline WHERE iata_code = :code"), {"code": inventory.airline_code})
    db.execute(text("DELETE FROM city_near_apt WHERE city_name IN (:dep_city, :arr_city)"), {"dep_city": inventory.dep_city, "arr_city": inventory.arr_city})
    db.execute(text("DELETE FROM airport WHERE iata_code IN (:dep_airport, :arr_airport)"), {"dep_airport": inventory.dep_airport, "arr_airport": inventory.arr_airport})
    db.execute(text("DELETE FROM city WHERE city_name IN (:dep_city, :arr_city)"), {"dep_city": inventory.dep_city, "arr_city": inventory.arr_city})


if __name__ == "__main__":
    raise SystemExit(main())
