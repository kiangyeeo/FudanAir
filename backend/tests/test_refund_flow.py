from __future__ import annotations

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.constants import REFUND_FEE_TIERS
from app.core.exceptions import (
    InstanceNotBookableError,
    ResourceNotFoundError,
    SameTicketNotAllowedError,
    TicketNotRefundableError,
)
from app.workflows.refund.service import RefundService


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
        future = datetime.now() + timedelta(days=10)
        past = datetime.now() - timedelta(days=1)
        self.details = {
            "OLD": self._detail(future, Decimal("50.00"), Decimal("800.00")),
            "NEW": self._detail(future, Decimal("50.00"), Decimal("1000.00")),
            "PAST": self._detail(past, Decimal("50.00"), Decimal("800.00")),
        }
        self.restore_calls: list[tuple[str, str, str, int]] = []
        self.deduct_calls: list[tuple[str, str, str, int]] = []
        self.bookable_checks: list[str] = []

    def get_instance_detail(self, instance_id: str) -> dict[str, Any]:
        return self.details[instance_id]

    def ensure_instance_bookable(self, instance_id: str) -> None:
        self.bookable_checks.append(instance_id)
        detail = self.details[instance_id]
        departure_at = datetime.combine(detail["flight_date"], detail["scheduled_departure"])
        if departure_at <= datetime.now():
            raise InstanceNotBookableError(f"航班实例 {instance_id} 已起飞,不可订")

    def restore_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int,
    ) -> None:
        self.restore_calls.append((instance_id, cabin_class, fare_type, quantity))

    def deduct_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int,
    ) -> SimpleNamespace:
        self.deduct_calls.append((instance_id, cabin_class, fare_type, quantity))
        return self._cabin_price(Decimal("1000.00"))

    @staticmethod
    def _detail(
        departure_at: datetime,
        fuel_fee: Decimal,
        ticket_price: Decimal,
    ) -> dict[str, Any]:
        return {
            "flight_date": departure_at.date(),
            "scheduled_departure": departure_at.time(),
            "fuel_infra_fee": fuel_fee,
            "cabin_prices": [FakeFlightService._cabin_price(ticket_price)],
        }

    @staticmethod
    def _cabin_price(price: Decimal) -> SimpleNamespace:
        return SimpleNamespace(cabin_class="经济舱", fare_type="标准", price=price)


class FakeOrderService:
    def __init__(self) -> None:
        self.order = SimpleNamespace(order_no="O1", user_id=7, status="已支付")
        self.status_updates: list[str] = []

    def lock_for_update(self, _order_no: str) -> SimpleNamespace:
        return self.order

    def update_status(self, order: SimpleNamespace, status: str) -> SimpleNamespace:
        order.status = status
        self.status_updates.append(status)
        return order


class FakeTicketService:
    def __init__(self) -> None:
        self.ticket = SimpleNamespace(
            ticket_no="T1",
            order_no="O1",
            passenger_id="P1",
            instance_id="OLD",
            cabin_class="经济舱",
            fare_type="标准",
            actual_price=Decimal("850.00"),
            status="有效",
        )
        self.tickets = [self.ticket]
        self.status_updates: list[tuple[str, str]] = []
        self.duplicate_checks: list[tuple[str, str]] = []

    def lock_for_update(self, _ticket_no: str) -> SimpleNamespace:
        return self.ticket

    def update_status(self, ticket: SimpleNamespace, status: str) -> SimpleNamespace:
        ticket.status = status
        self.status_updates.append((ticket.ticket_no, status))
        return ticket

    def list_by_order(self, _order_no: str) -> list[SimpleNamespace]:
        return self.tickets

    def check_passenger_duplicate(self, passenger_id: str, instance_id: str) -> None:
        self.duplicate_checks.append((passenger_id, instance_id))

    def create(
        self,
        order_no: str,
        passenger_id: str,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        actual_price: Decimal,
        status: str = "有效",
    ) -> SimpleNamespace:
        ticket = SimpleNamespace(
            ticket_no=f"T{len(self.tickets) + 1}",
            order_no=order_no,
            passenger_id=passenger_id,
            instance_id=instance_id,
            cabin_class=cabin_class,
            fare_type=fare_type,
            actual_price=actual_price,
            status=status,
        )
        self.tickets.append(ticket)
        return ticket


class FakeRefundChangeService:
    def __init__(self) -> None:
        self.records: list[SimpleNamespace] = []

    def create_record(
        self,
        ticket_no: str,
        op_type: str,
        fee: Decimal,
        new_ticket_no: str | None = None,
        price_diff: Decimal = Decimal("0.00"),
    ) -> SimpleNamespace:
        record = SimpleNamespace(
            refund_id=1001 + len(self.records),
            ticket_no=ticket_no,
            op_type=op_type,
            fee=fee,
            new_ticket_no=new_ticket_no,
            price_diff=price_diff,
        )
        self.records.append(record)
        return record


def make_service() -> RefundService:
    service = RefundService.__new__(RefundService)
    service.db = FakeSession()
    service.flight_svc = FakeFlightService()
    service.order_svc = FakeOrderService()
    service.ticket_svc = FakeTicketService()
    service.refund_svc = FakeRefundChangeService()
    return service


def test_quote_uses_refund_fee_tiers_for_refund_and_change() -> None:
    service = make_service()

    refund_quote = service.quote(7, "T1", "refund")
    change_quote = service.quote(7, "T1", "change", "NEW", "经济舱", "标准")

    assert refund_quote["fee_rate"] == Decimal(str(REFUND_FEE_TIERS[1][1]))
    assert refund_quote["fee"] == Decimal("170.00")
    assert refund_quote["refund_amount"] == Decimal("680.00")
    assert refund_quote["tier"] == "7-30天"
    assert change_quote["fee_rate"] == Decimal(str(REFUND_FEE_TIERS[1][2]))
    assert change_quote["new_actual_price"] == Decimal("1050.00")
    assert change_quote["price_diff"] == Decimal("200.00")
    assert change_quote["amount_user_pays"] == Decimal("370.00")


def test_refund_ticket_updates_ticket_stock_record_and_order_status() -> None:
    service = make_service()

    response = service.refund_ticket(7, "T1")

    assert service.ticket_svc.status_updates == [("T1", "已退")]
    assert service.flight_svc.restore_calls == [("OLD", "经济舱", "标准", 1)]
    assert service.refund_svc.records[0].op_type == "退票"
    assert service.refund_svc.records[0].fee == Decimal("170.00")
    assert service.order_svc.status_updates == ["已完成退款"]
    assert response["ticket_status"] == "已退"
    assert response["refund_amount"] == Decimal("680.00")


def test_change_ticket_replaces_old_ticket_and_creates_refund_record() -> None:
    service = make_service()

    response = service.change_ticket(7, "T1", "NEW", "经济舱", "标准")

    assert service.ticket_svc.status_updates == [("T1", "已改签作废")]
    assert service.ticket_svc.duplicate_checks == [("P1", "NEW")]
    assert service.flight_svc.restore_calls == [("OLD", "经济舱", "标准", 1)]
    assert service.flight_svc.deduct_calls == [("NEW", "经济舱", "标准", 1)]
    assert service.ticket_svc.tickets[1].actual_price == Decimal("1050.00")
    assert service.refund_svc.records[0].op_type == "改签"
    assert service.refund_svc.records[0].new_ticket_no == "T2"
    assert service.refund_svc.records[0].price_diff == Decimal("200.00")
    assert service.order_svc.status_updates == []
    assert response["new_ticket_no"] == "T2"
    assert response["amount_user_pays"] == Decimal("370.00")
    assert service.flight_svc.bookable_checks == ["NEW"]


def test_refund_rejects_ticket_from_other_user() -> None:
    service = make_service()
    service.order_svc.order.user_id = 8

    with pytest.raises(ResourceNotFoundError):
        service.refund_ticket(7, "T1")


def test_refund_rejects_non_active_ticket() -> None:
    service = make_service()
    service.ticket_svc.ticket.status = "已退"

    with pytest.raises(TicketNotRefundableError):
        service.refund_ticket(7, "T1")


def test_refund_rejects_departed_flight() -> None:
    service = make_service()
    service.ticket_svc.ticket.instance_id = "PAST"

    with pytest.raises(TicketNotRefundableError):
        service.quote(7, "T1", "refund")


def test_change_rejects_same_target_by_ac3() -> None:
    service = make_service()

    with pytest.raises(SameTicketNotAllowedError):
        service.change_ticket(7, "T1", "OLD", "经济舱", "标准")


def test_change_quote_rejects_departed_target() -> None:
    service = make_service()

    with pytest.raises(InstanceNotBookableError):
        service.quote(7, "T1", "change", "PAST", "经济舱", "标准")


def test_change_ticket_rejects_departed_target_before_mutation() -> None:
    service = make_service()

    with pytest.raises(InstanceNotBookableError):
        service.change_ticket(7, "T1", "PAST", "经济舱", "标准")

    assert service.ticket_svc.status_updates == []
    assert service.flight_svc.restore_calls == []
    assert service.flight_svc.deduct_calls == []
