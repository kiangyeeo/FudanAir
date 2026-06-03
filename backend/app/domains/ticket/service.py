from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import (
    AppException,
    PassengerDuplicateError,
    ResourceNotFoundError,
)
from app.core.id_generator import gen_ticket_no
from app.domains.ticket.models import RefundChange, Ticket
from app.domains.ticket.repository import RefundChangeRepository, TicketRepository


ALLOWED_TICKET_STATUSES = {"有效", "已退", "已改签作废", "已使用"}
ALLOWED_REFUND_OP_TYPES = {"退票", "改签"}


class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TicketRepository(db)

    def create(
        self,
        order_no: str,
        passenger_id: str,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        actual_price: Decimal,
        fuel_infra_fee: Decimal,
        status: str = "有效",
    ) -> Ticket:
        try:
            with transaction(self.db):
                return self.repo.create(
                    ticket_no=gen_ticket_no(self.repo.next_ticket_sequence()),
                    order_no=order_no,
                    passenger_id=passenger_id,
                    instance_id=instance_id,
                    cabin_class=cabin_class,
                    fare_type=fare_type,
                    actual_price=actual_price,
                    fuel_infra_fee=fuel_infra_fee,
                    status=_ticket_status(status),
                )
        except IntegrityError as exc:
            raise AppException("客票创建失败") from exc

    def lock_for_update(self, ticket_no: str) -> Ticket:
        ticket = self.repo.lock_for_update(ticket_no)
        if not ticket:
            raise ResourceNotFoundError(f"客票 {ticket_no} 不存在")
        return ticket

    def update_status(self, ticket: Ticket, status: str) -> Ticket:
        try:
            with transaction(self.db):
                return self.repo.update_status(ticket, _ticket_status(status))
        except IntegrityError as exc:
            raise AppException(f"客票 {ticket.ticket_no} 状态更新失败") from exc

    def list_by_order(self, order_no: str) -> list[Ticket]:
        return self.repo.list_by_order(order_no)

    def check_passenger_duplicate(self, passenger_id: str, instance_id: str) -> None:
        if self.repo.has_active_ticket(passenger_id, instance_id):
            raise PassengerDuplicateError()


class RefundChangeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RefundChangeRepository(db)

    def create_record(
        self,
        ticket_no: str,
        op_type: str,
        fee: Decimal,
        new_ticket_no: str | None = None,
        price_diff: Decimal = Decimal("0.00"),
    ) -> RefundChange:
        normalized_type = _refund_op_type(op_type)
        self._validate_record(normalized_type, new_ticket_no, price_diff)
        try:
            with transaction(self.db):
                return self.repo.create(
                    ticket_no=ticket_no,
                    op_type=normalized_type,
                    fee=fee,
                    new_ticket_no=new_ticket_no,
                    price_diff=price_diff,
                    op_time=datetime.now(),
                )
        except IntegrityError as exc:
            raise AppException("退改记录创建失败") from exc

    def list_by_user(self, user_id: int, page: int, page_size: int) -> dict[str, object]:
        items, total = self.repo.list_by_user(user_id, page, page_size)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    def _validate_record(
        op_type: str,
        new_ticket_no: str | None,
        price_diff: Decimal,
    ) -> None:
        if op_type == "退票" and (new_ticket_no is not None or price_diff != Decimal("0.00")):
            raise AppException("退票记录字段不合法")
        if op_type == "改签" and new_ticket_no is None:
            raise AppException("改签记录缺少新票号")


def _ticket_status(value: str) -> str:
    normalized = value.strip()
    if normalized not in ALLOWED_TICKET_STATUSES:
        raise AppException("客票状态不合法")
    return normalized


def _refund_op_type(value: str) -> str:
    normalized = value.strip()
    if normalized not in ALLOWED_REFUND_OP_TYPES:
        raise AppException("退改类型不合法")
    return normalized
