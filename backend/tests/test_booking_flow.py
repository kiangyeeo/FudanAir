from __future__ import annotations

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.exceptions import PassengerDuplicateError
from app.workflows.booking.schemas import BookingRequest
from app.workflows.booking.service import BookingService


class FakeTransaction:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.info: dict[str, Any] = {}

    def in_transaction(self) -> bool:
        return True

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeFlightService:
    def __init__(self) -> None:
        self.deduct_calls: list[tuple[str, str, str, int]] = []
        self.restore_calls: list[tuple[str, str, str, int]] = []

    def deduct_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int,
    ) -> SimpleNamespace:
        self.deduct_calls.append((instance_id, cabin_class, fare_type, quantity))
        return SimpleNamespace(price=Decimal("800.00"))

    def restore_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int,
    ) -> None:
        self.restore_calls.append((instance_id, cabin_class, fare_type, quantity))

    def get_instance_detail(self, _instance_id: str) -> dict[str, Decimal]:
        return {"fuel_infra_fee": Decimal("50.00")}


class FakeOrderService:
    def __init__(self) -> None:
        self.order = SimpleNamespace(
            order_no="O202605120001",
            user_id=7,
            total_amount=Decimal("0.00"),
            status="待支付",
            created_at=datetime.now(),
        )
        self.status_updates: list[str] = []

    def create(self, user_id: int, total_amount: Decimal) -> SimpleNamespace:
        self.order.user_id = user_id
        self.order.total_amount = total_amount
        return self.order

    def lock_for_update(self, _order_no: str) -> SimpleNamespace:
        return self.order

    def update_status(self, order: SimpleNamespace, status: str) -> SimpleNamespace:
        order.status = status
        self.status_updates.append(status)
        return order


class FakeTicketService:
    def __init__(self) -> None:
        self.duplicate_checks: list[tuple[str, str]] = []
        self.tickets: list[SimpleNamespace] = []
        self.status_updates: list[tuple[str, str]] = []

    def check_passenger_duplicate(self, passenger_id: str, instance_id: str) -> None:
        self.duplicate_checks.append((passenger_id, instance_id))
        for ticket in self.tickets:
            if (
                ticket.passenger_id == passenger_id
                and ticket.instance_id == instance_id
                and ticket.status == "有效"
            ):
                raise PassengerDuplicateError()

    def create(
        self,
        order_no: str,
        passenger_id: str,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        actual_price: Decimal,
        fuel_infra_fee: Decimal,
    ) -> SimpleNamespace:
        ticket = SimpleNamespace(
            ticket_no=f"T{len(self.tickets) + 1}",
            order_no=order_no,
            passenger_id=passenger_id,
            instance_id=instance_id,
            cabin_class=cabin_class,
            fare_type=fare_type,
            actual_price=actual_price,
            fuel_infra_fee=fuel_infra_fee,
            status="有效",
        )
        self.tickets.append(ticket)
        return ticket

    def list_by_order(self, _order_no: str) -> list[SimpleNamespace]:
        return self.tickets

    def update_status(self, ticket: SimpleNamespace, status: str) -> SimpleNamespace:
        ticket.status = status
        self.status_updates.append((ticket.ticket_no, status))
        return ticket


class FakePassengerService:
    def __init__(self) -> None:
        self.saved: list[tuple[int, str, str, date]] = []

    def save_for_user(self, user_id: int, id_no: str, real_name: str, birth_date: date) -> None:
        self.saved.append((user_id, id_no, real_name, birth_date))


def make_service() -> BookingService:
    service = BookingService.__new__(BookingService)
    service.db = FakeSession()
    service.flight_svc = FakeFlightService()
    service.order_svc = FakeOrderService()
    service.ticket_svc = FakeTicketService()
    service.passenger_svc = FakePassengerService()
    return service


def test_create_order_deducts_stock_and_price_includes_fuel_fee() -> None:
    service = make_service()
    payload = BookingRequest.model_validate(
        {
            "instance_id": "MU1001_20260512",
            "cabin_class": "经济舱",
            "fare_type": "标准",
            "passengers": [
                {
                    "id_no": "110101199001011234",
                    "real_name": "张三",
                    "birth_date": "1990-01-01",
                },
                {
                    "id_no": "110101199203033456",
                    "real_name": "李四",
                    "birth_date": "1992-03-03",
                },
            ],
        }
    )

    response = service.create_order(7, payload)

    assert service.flight_svc.deduct_calls == [
        ("MU1001_20260512", "经济舱", "标准", 2)
    ]
    assert service.ticket_svc.duplicate_checks == [
        ("110101199001011234", "MU1001_20260512"),
        ("110101199203033456", "MU1001_20260512"),
    ]
    assert service.order_svc.order.total_amount == Decimal("1700.00")
    assert service.passenger_svc.saved == [
        (7, "110101199001011234", "张三", date(1990, 1, 1)),
        (7, "110101199203033456", "李四", date(1992, 3, 3)),
    ]
    assert response["amount_breakdown"]["fuel_infra_fee_per_seat"] == Decimal("50.00")
    assert response["amount_breakdown"]["segments"][0]["ticket_price_per_seat"] == Decimal("800.00")
    assert response["tickets"][0]["actual_price"] == Decimal("850.00")


def test_create_order_allows_rebooking_after_refund() -> None:
    service = make_service()
    service.ticket_svc.tickets = [
        SimpleNamespace(
            ticket_no="T0",
            passenger_id="110101199001011234",
            instance_id="MU1001_20260512",
            cabin_class="经济舱",
            fare_type="标准",
            actual_price=Decimal("850.00"),
            status="已退",
        )
    ]
    payload = BookingRequest.model_validate(
        {
            "instance_id": "MU1001_20260512",
            "cabin_class": "经济舱",
            "fare_type": "标准",
            "passengers": [
                {
                    "id_no": "110101199001011234",
                    "real_name": "张三",
                    "birth_date": "1990-01-01",
                }
            ],
        }
    )

    response = service.create_order(7, payload)

    assert service.ticket_svc.duplicate_checks == [
        ("110101199001011234", "MU1001_20260512")
    ]
    assert len(response["tickets"]) == 1
    assert response["tickets"][0]["passenger_id"] == "110101199001011234"


def test_create_order_can_book_transit_segments_in_one_order() -> None:
    service = make_service()
    payload = BookingRequest.model_validate(
        {
            "segments": [
                {
                    "instance_id": "MU1001_20260512",
                    "cabin_class": "经济舱",
                    "fare_type": "标准",
                },
                {
                    "instance_id": "CA2001_20260512",
                    "cabin_class": "经济舱",
                    "fare_type": "标准",
                },
            ],
            "passengers": [
                {
                    "id_no": "110101199001011234",
                    "real_name": "张三",
                    "birth_date": "1990-01-01",
                },
                {
                    "id_no": "110101199203033456",
                    "real_name": "李四",
                    "birth_date": "1992-03-03",
                },
            ],
        }
    )

    response = service.create_order(7, payload)

    assert service.flight_svc.deduct_calls == [
        ("MU1001_20260512", "经济舱", "标准", 2),
        ("CA2001_20260512", "经济舱", "标准", 2),
    ]
    assert service.order_svc.order.total_amount == Decimal("3400.00")
    assert len(response["tickets"]) == 4
    assert response["amount_breakdown"]["segment_count"] == 2
    assert response["amount_breakdown"]["passenger_count"] == 2


def test_pay_order_only_updates_order_status() -> None:
    service = make_service()

    response = service.pay_order(7, "O202605120001")

    assert response["status"] == "已支付"
    assert service.order_svc.status_updates == ["已支付"]
    assert service.flight_svc.deduct_calls == []
    assert service.flight_svc.restore_calls == []


def test_cancel_order_refunds_active_tickets_and_restores_stock() -> None:
    service = make_service()
    service.ticket_svc.tickets = [
        SimpleNamespace(
            ticket_no="T1",
            instance_id="MU1001_20260512",
            cabin_class="经济舱",
            fare_type="标准",
            status="有效",
        )
    ]

    service.cancel_order(7, "O202605120001")

    assert service.flight_svc.restore_calls == [
        ("MU1001_20260512", "经济舱", "标准", 1)
    ]
    assert service.ticket_svc.status_updates == [("T1", "已退")]
    assert service.order_svc.status_updates == ["已取消"]
