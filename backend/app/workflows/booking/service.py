from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import transaction
from app.core.exceptions import (
    OrderNotCancelableError,
    OrderNotPayableError,
    PassengerDuplicateError,
    ResourceNotFoundError,
)
from app.core.logging import get_logger
from app.domains.flight.service import FlightService
from app.domains.order.models import AptOrder
from app.domains.order.service import OrderService
from app.domains.ticket.models import Ticket
from app.domains.ticket.service import TicketService
from app.domains.passenger.service import PassengerService
from app.workflows.booking.schemas import BookingRequest, BookingSegment


ORDER_STATUS_PENDING = "待支付"
ORDER_STATUS_PAID = "已支付"
ORDER_STATUS_CANCELED = "已取消"
TICKET_STATUS_ACTIVE = "有效"
TICKET_STATUS_REFUNDED = "已退"
MONEY_QUANT = Decimal("0.01")

logger = get_logger(__name__)


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.flight_svc = FlightService(db)
        self.order_svc = OrderService(db)
        self.ticket_svc = TicketService(db)
        self.passenger_svc = PassengerService(db)

    def create_order(self, user_id: int, payload: BookingRequest) -> dict[str, Any]:
        passenger_count = len(payload.passengers)
        segments = _booking_segments(payload)
        _ensure_unique_payload_passengers(payload)
        _ensure_unique_payload_segments(segments)
        with transaction(self.db):
            for passenger in payload.passengers:
                self.passenger_svc.save_for_user(
                    user_id,
                    passenger.id_no,
                    passenger.real_name,
                    passenger.birth_date,
                )

            segment_prices = []
            total_amount = Decimal("0.00")
            for segment in segments:
                cabin_price = self.flight_svc.deduct_seat(
                    segment.instance_id,
                    segment.cabin_class,
                    segment.fare_type,
                    passenger_count,
                )
                instance_detail = self.flight_svc.get_instance_detail(segment.instance_id)
                fuel_fee = _money(instance_detail["fuel_infra_fee"])
                ticket_price = _money(cabin_price.price)
                actual_price = _money(ticket_price + fuel_fee)
                segment_prices.append(
                    {
                        "instance_id": segment.instance_id,
                        "cabin_class": segment.cabin_class,
                        "fare_type": segment.fare_type,
                        "ticket_price": ticket_price,
                        "fuel_fee": fuel_fee,
                        "actual_price": actual_price,
                    }
                )
                total_amount += actual_price * passenger_count
                for passenger in payload.passengers:
                    self.ticket_svc.check_passenger_duplicate(
                        passenger.id_no,
                        segment.instance_id,
                    )

            order = self.order_svc.create(user_id, total_amount)
            tickets = []
            for segment_price in segment_prices:
                for passenger in payload.passengers:
                    tickets.append(
                        self.ticket_svc.create(
                            order.order_no,
                            passenger.id_no,
                            segment_price["instance_id"],
                            segment_price["cabin_class"],
                            segment_price["fare_type"],
                            segment_price["actual_price"],
                            segment_price["fuel_fee"],
                        )
                    )

        instance_ids = ",".join(segment.instance_id for segment in segments)
        logger.info(
            "Booking created order_no=%s user_id=%s instances=%s passengers=%s tickets=%s",
            order.order_no,
            user_id,
            instance_ids,
            passenger_count,
            len(tickets),
        )
        return _booking_response(order, tickets, segment_prices, passenger_count)

    def pay_order(self, user_id: int, order_no: str) -> dict[str, Any]:
        expired = False
        with transaction(self.db):
            order = self.order_svc.lock_for_update(order_no)
            self._ensure_order_owner(order, user_id)
            if order.status != ORDER_STATUS_PENDING:
                raise OrderNotPayableError("Order status does not allow payment.")
            if self._is_expired(order):
                self._release_pending_order(order)
                expired = True
            else:
                self.order_svc.update_status(order, ORDER_STATUS_PAID)

        if expired:
            logger.info("Order expired during payment order_no=%s user_id=%s", order_no, user_id)
            raise OrderNotPayableError("Order has expired.")

        paid_at = datetime.now()
        logger.info("Payment succeeded order_no=%s user_id=%s paid_at=%s", order_no, user_id, paid_at)
        return {"order_no": order_no, "status": ORDER_STATUS_PAID, "paid_at": paid_at}

    def cancel_order(self, user_id: int, order_no: str) -> None:
        with transaction(self.db):
            order = self.order_svc.lock_for_update(order_no)
            self._ensure_order_owner(order, user_id)
            if order.status != ORDER_STATUS_PENDING:
                raise OrderNotCancelableError("Order status does not allow cancellation.")
            self._release_pending_order(order)
        logger.info("Order cancellation succeeded order_no=%s user_id=%s", order_no, user_id)

    def expire_order(self, order_no: str) -> bool:
        with transaction(self.db):
            order = self.order_svc.lock_for_update(order_no)
            if order.status != ORDER_STATUS_PENDING:
                return False
            self._release_pending_order(order)
        logger.info("Order expired and was canceled order_no=%s", order_no)
        return True

    def _release_pending_order(self, order: AptOrder) -> None:
        tickets = self.ticket_svc.list_by_order(order.order_no)
        for ticket in tickets:
            if ticket.status != TICKET_STATUS_ACTIVE:
                continue
            self.flight_svc.restore_seat(
                ticket.instance_id,
                ticket.cabin_class,
                ticket.fare_type,
                1,
            )
            self.ticket_svc.update_status(ticket, TICKET_STATUS_REFUNDED)
        self.order_svc.update_status(order, ORDER_STATUS_CANCELED)

    @staticmethod
    def _ensure_order_owner(order: AptOrder, user_id: int) -> None:
        if int(order.user_id) != user_id:
            raise ResourceNotFoundError(f"Order {order.order_no} does not exist")

    @staticmethod
    def _is_expired(order: AptOrder) -> bool:
        expires_at = order.created_at + timedelta(minutes=settings.ORDER_EXPIRE_MINUTES)
        return datetime.now() >= expires_at


def _booking_response(
    order: AptOrder,
    tickets: list[Ticket],
    segment_prices: list[dict[str, Any]],
    passenger_count: int,
) -> dict[str, Any]:
    ticket_price = _money(sum((item["ticket_price"] for item in segment_prices), Decimal("0.00")))
    fuel_fee = _money(sum((item["fuel_fee"] for item in segment_prices), Decimal("0.00")))
    return {
        "order_no": order.order_no,
        "status": order.status,
        "total_amount": order.total_amount,
        "amount_breakdown": {
            "ticket_price_per_seat": ticket_price,
            "fuel_infra_fee_per_seat": fuel_fee,
            "seat_count": passenger_count,
            "passenger_count": passenger_count,
            "segment_count": len(segment_prices),
            "segments": [
                {
                    "instance_id": item["instance_id"],
                    "cabin_class": item["cabin_class"],
                    "fare_type": item["fare_type"],
                    "ticket_price_per_seat": item["ticket_price"],
                    "fuel_infra_fee_per_seat": item["fuel_fee"],
                    "actual_price_per_seat": item["actual_price"],
                    "passenger_count": passenger_count,
                    "subtotal": item["actual_price"] * passenger_count,
                }
                for item in segment_prices
            ],
        },
        "created_at": order.created_at,
        "expires_at": order.created_at + timedelta(minutes=settings.ORDER_EXPIRE_MINUTES),
        "tickets": [
            {
                "ticket_no": ticket.ticket_no,
                "passenger_id": ticket.passenger_id,
                "instance_id": ticket.instance_id,
                "cabin_class": ticket.cabin_class,
                "fare_type": ticket.fare_type,
                "actual_price": ticket.actual_price,
            }
            for ticket in tickets
        ],
    }


def _money(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(MONEY_QUANT)
    return Decimal(str(value)).quantize(MONEY_QUANT)


def _ensure_unique_payload_passengers(payload: BookingRequest) -> None:
    passenger_ids = [passenger.id_no for passenger in payload.passengers]
    if len(passenger_ids) != len(set(passenger_ids)):
        raise PassengerDuplicateError("Passengers in the same order cannot be duplicated.")


def _ensure_unique_payload_segments(segments: list[BookingSegment]) -> None:
    instance_ids = [segment.instance_id for segment in segments]
    if len(instance_ids) != len(set(instance_ids)):
        raise PassengerDuplicateError("The same flight instance cannot be selected more than once in one order.")


def _booking_segments(payload: BookingRequest) -> list[BookingSegment]:
    if payload.segments:
        return payload.segments
    return [
        BookingSegment(
            instance_id=payload.instance_id or "",
            cabin_class=payload.cabin_class or "经济舱",
            fare_type=payload.fare_type or "标准",
        )
    ]
