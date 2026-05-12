from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import REFUND_FEE_TIERS
from app.core.database import transaction
from app.core.exceptions import (
    AppException,
    ResourceNotFoundError,
    SameTicketNotAllowedError,
    TicketNotChangeableError,
    TicketNotRefundableError,
)
from app.core.logging import get_logger
from app.domains.flight.service import FlightService
from app.domains.order.models import AptOrder
from app.domains.order.service import OrderService
from app.domains.ticket.models import Ticket
from app.domains.ticket.service import RefundChangeService, TicketService


ORDER_STATUS_PAID = "已支付"
ORDER_STATUS_PARTIAL_REFUND = "部分退款"
ORDER_STATUS_FULL_REFUND = "已完成退款"
TICKET_STATUS_ACTIVE = "有效"
TICKET_STATUS_REFUNDED = "已退"
TICKET_STATUS_CHANGED = "已改签作废"
RECORD_OP_TYPE = {"refund": "退票", "change": "改签"}
MONEY_QUANT = Decimal("0.01")

logger = get_logger(__name__)


class RefundService:
    def __init__(self, db: Session):
        self.db = db
        self.flight_svc = FlightService(db)
        self.order_svc = OrderService(db)
        self.ticket_svc = TicketService(db)
        self.refund_svc = RefundChangeService(db)

    def quote(
        self,
        user_id: int,
        ticket_no: str,
        op_type: str,
        new_instance_id: str | None = None,
        new_cabin_class: str | None = None,
        new_fare_type: str | None = None,
    ) -> dict[str, Any]:
        with transaction(self.db):
            ticket, _order = self._lock_ticket_order(user_id, ticket_no, op_type)
            fee_quote = self._fee_quote(ticket, op_type)
            if op_type == "refund":
                return self._refund_quote_response(ticket, fee_quote)
            target = _change_target(new_instance_id, new_cabin_class, new_fare_type)
            self._ensure_not_same_target(ticket, target)
            new_actual_price = self._new_actual_price(target)
            return self._change_quote_response(ticket, fee_quote, new_actual_price)

    def refund_ticket(self, user_id: int, ticket_no: str) -> dict[str, Any]:
        with transaction(self.db):
            ticket, order = self._lock_ticket_order(user_id, ticket_no, "refund")
            fee_quote = self._fee_quote(ticket, "refund")
            self.ticket_svc.update_status(ticket, TICKET_STATUS_REFUNDED)
            self.flight_svc.restore_seat(ticket.instance_id, ticket.cabin_class, ticket.fare_type, 1)
            record = self.refund_svc.create_record(
                ticket.ticket_no,
                RECORD_OP_TYPE["refund"],
                fee_quote["fee"],
            )
            order_status = self._sync_refund_order_status(order)

        logger.info("退票成功 ticket_no=%s user_id=%s refund_id=%s", ticket_no, user_id, record.refund_id)
        return {
            "refund_id": record.refund_id,
            "ticket_no": ticket.ticket_no,
            "fee": fee_quote["fee"],
            "refund_amount": _money(_ticket_price(ticket) - fee_quote["fee"]),
            "ticket_status": ticket.status,
            "order_status": order_status,
        }

    def change_ticket(
        self,
        user_id: int,
        ticket_no: str,
        new_instance_id: str,
        new_cabin_class: str,
        new_fare_type: str,
    ) -> dict[str, Any]:
        target = _change_target(new_instance_id, new_cabin_class, new_fare_type)
        with transaction(self.db):
            old_ticket, _order = self._lock_ticket_order(user_id, ticket_no, "change")
            self._ensure_not_same_target(old_ticket, target)
            fee_quote = self._fee_quote(old_ticket, "change")
            new_ticket, price_diff = self._replace_ticket(old_ticket, target)
            record = self.refund_svc.create_record(
                old_ticket.ticket_no,
                RECORD_OP_TYPE["change"],
                fee_quote["fee"],
                new_ticket_no=new_ticket.ticket_no,
                price_diff=price_diff,
            )

        logger.info(
            "改签成功 old_ticket_no=%s new_ticket_no=%s user_id=%s refund_id=%s",
            old_ticket.ticket_no,
            new_ticket.ticket_no,
            user_id,
            record.refund_id,
        )
        return {
            "refund_id": record.refund_id,
            "old_ticket_no": old_ticket.ticket_no,
            "new_ticket_no": new_ticket.ticket_no,
            "fee": fee_quote["fee"],
            "price_diff": price_diff,
            "amount_user_pays": _money(fee_quote["fee"] + price_diff),
            "old_ticket_status": old_ticket.status,
            "new_ticket_status": new_ticket.status,
        }

    def _lock_ticket_order(
        self,
        user_id: int,
        ticket_no: str,
        op_type: str,
    ) -> tuple[Ticket, AptOrder]:
        ticket = self.ticket_svc.lock_for_update(ticket_no.strip())
        order = self.order_svc.lock_for_update(ticket.order_no)
        if int(order.user_id) != user_id:
            raise ResourceNotFoundError(f"客票 {ticket_no} 不存在")
        self._ensure_ticket_operable(ticket, order, op_type)
        return ticket, order

    def _ensure_ticket_operable(self, ticket: Ticket, order: AptOrder, op_type: str) -> None:
        if ticket.status != TICKET_STATUS_ACTIVE:
            _raise_ticket_not_operable(op_type, "客票状态不允许退改")
        if order.status not in {ORDER_STATUS_PAID, ORDER_STATUS_PARTIAL_REFUND}:
            _raise_ticket_not_operable(op_type, "订单状态不允许退改")

    def _fee_quote(self, ticket: Ticket, op_type: str) -> dict[str, Any]:
        detail = self.flight_svc.get_instance_detail(ticket.instance_id)
        departure_at = _departure_at(detail)
        now = datetime.now()
        if departure_at <= now:
            _raise_ticket_not_operable(op_type, "航班已起飞,不可退改")
        fee_rate, tier = _fee_rate(departure_at - now, op_type)
        fee = _money(_ticket_price(ticket) * fee_rate)
        return {"fee_rate": fee_rate, "fee": fee, "tier": tier}

    def _new_actual_price(self, target: dict[str, str]) -> Decimal:
        detail = self.flight_svc.get_instance_detail(target["instance_id"])
        for cabin_price in detail["cabin_prices"]:
            if cabin_price.cabin_class == target["cabin_class"] and cabin_price.fare_type == target["fare_type"]:
                return _money(_decimal(cabin_price.price) + _decimal(detail["fuel_infra_fee"]))
        raise ResourceNotFoundError("舱位价格档位不存在")

    def _actual_price_with_fuel(self, instance_id: str, ticket_price: Decimal) -> Decimal:
        detail = self.flight_svc.get_instance_detail(instance_id)
        return _money(_decimal(ticket_price) + _decimal(detail["fuel_infra_fee"]))

    def _replace_ticket(
        self,
        old_ticket: Ticket,
        target: dict[str, str],
    ) -> tuple[Ticket, Decimal]:
        self.ticket_svc.update_status(old_ticket, TICKET_STATUS_CHANGED)
        self.flight_svc.restore_seat(
            old_ticket.instance_id,
            old_ticket.cabin_class,
            old_ticket.fare_type,
            1,
        )
        self.ticket_svc.check_passenger_duplicate(old_ticket.passenger_id, target["instance_id"])
        new_ticket = self._create_new_ticket(old_ticket, target)
        if new_ticket.ticket_no == old_ticket.ticket_no:
            raise SameTicketNotAllowedError()
        return new_ticket, _money(new_ticket.actual_price - _ticket_price(old_ticket))

    def _create_new_ticket(self, old_ticket: Ticket, target: dict[str, str]) -> Ticket:
        cabin_price = self.flight_svc.deduct_seat(
            target["instance_id"],
            target["cabin_class"],
            target["fare_type"],
            1,
        )
        actual_price = self._actual_price_with_fuel(target["instance_id"], cabin_price.price)
        return self.ticket_svc.create(
            old_ticket.order_no,
            old_ticket.passenger_id,
            target["instance_id"],
            target["cabin_class"],
            target["fare_type"],
            actual_price,
            status=TICKET_STATUS_ACTIVE,
        )

    def _sync_refund_order_status(self, order: AptOrder) -> str:
        active_count = sum(
            1 for item in self.ticket_svc.list_by_order(order.order_no) if item.status == TICKET_STATUS_ACTIVE
        )
        next_status = ORDER_STATUS_PARTIAL_REFUND if active_count else ORDER_STATUS_FULL_REFUND
        self.order_svc.update_status(order, next_status)
        return next_status

    @staticmethod
    def _ensure_not_same_target(ticket: Ticket, target: dict[str, str]) -> None:
        if (
            ticket.instance_id == target["instance_id"]
            and ticket.cabin_class == target["cabin_class"]
            and ticket.fare_type == target["fare_type"]
        ):
            raise SameTicketNotAllowedError()

    @staticmethod
    def _refund_quote_response(ticket: Ticket, fee_quote: dict[str, Any]) -> dict[str, Any]:
        actual_price = _ticket_price(ticket)
        return {
            "ticket_no": ticket.ticket_no,
            "op_type": "refund",
            "actual_price": actual_price,
            "fee_rate": fee_quote["fee_rate"],
            "fee": fee_quote["fee"],
            "refund_amount": _money(actual_price - fee_quote["fee"]),
            "tier": fee_quote["tier"],
        }

    @staticmethod
    def _change_quote_response(
        ticket: Ticket,
        fee_quote: dict[str, Any],
        new_actual_price: Decimal,
    ) -> dict[str, Any]:
        old_actual_price = _ticket_price(ticket)
        price_diff = _money(new_actual_price - old_actual_price)
        return {
            "ticket_no": ticket.ticket_no,
            "op_type": "change",
            "old_actual_price": old_actual_price,
            "new_actual_price": new_actual_price,
            "fee_rate": fee_quote["fee_rate"],
            "fee": fee_quote["fee"],
            "price_diff": price_diff,
            "amount_user_pays": _money(fee_quote["fee"] + price_diff),
            "tier": fee_quote["tier"],
        }


def _change_target(
    instance_id: str | None,
    cabin_class: str | None,
    fare_type: str | None,
) -> dict[str, str]:
    target = {
        "instance_id": (instance_id or "").strip(),
        "cabin_class": (cabin_class or "").strip(),
        "fare_type": (fare_type or "").strip(),
    }
    if not target["instance_id"] or not target["cabin_class"] or not target["fare_type"]:
        raise TicketNotChangeableError("缺少改签目标信息")
    return target


def _raise_ticket_not_operable(op_type: str, message: str) -> None:
    if op_type == "refund":
        raise TicketNotRefundableError(message)
    raise TicketNotChangeableError(message)


def _fee_rate(delta: timedelta, op_type: str) -> tuple[Decimal, str]:
    days_until_departure = Decimal(str(delta.total_seconds())) / Decimal(
        str(timedelta(days=1).total_seconds())
    )
    tiers = sorted(REFUND_FEE_TIERS, key=lambda item: item[0], reverse=True)
    for index, tier in enumerate(tiers):
        threshold, refund_rate, change_rate = tier
        if days_until_departure >= Decimal(str(threshold)):
            rate = refund_rate if op_type == "refund" else change_rate
            return Decimal(str(rate)), _tier_label(index, tiers)
    raise AppException("退改费率配置不合法")


def _tier_label(index: int, tiers: list[tuple[int, float, float]]) -> str:
    threshold = tiers[index][0]
    if index == 0:
        return f"≥{threshold}天"
    previous_threshold = tiers[index - 1][0]
    if index == len(tiers) - 1:
        return f"<{previous_threshold}天"
    return f"{threshold}-{previous_threshold}天"


def _departure_at(detail: dict[str, Any]) -> datetime:
    flight_date = detail["flight_date"]
    departure = detail["scheduled_departure"]
    if isinstance(departure, timedelta):
        return datetime.combine(flight_date, time.min) + departure
    if isinstance(departure, str):
        departure = time.fromisoformat(departure)
    return datetime.combine(flight_date, departure)


def _ticket_price(ticket: Ticket) -> Decimal:
    return _money(ticket.actual_price)


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: object) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANT)
