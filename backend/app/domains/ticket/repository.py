from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domains.ticket.models import RefundChange, Ticket


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, ticket_no: str) -> Ticket | None:
        return self.db.get(Ticket, ticket_no)

    def lock_for_update(self, ticket_no: str) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.ticket_no == ticket_no).with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        ticket_no: str,
        order_no: str,
        passenger_id: str,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        actual_price: Decimal,
        fuel_infra_fee: Decimal,
        status: str,
    ) -> Ticket:
        ticket = Ticket(
            ticket_no=ticket_no,
            order_no=order_no,
            passenger_id=passenger_id,
            instance_id=instance_id,
            cabin_class=cabin_class,
            fare_type=fare_type,
            actual_price=actual_price,
            fuel_infra_fee=fuel_infra_fee,
            status=status,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def update_status(self, ticket: Ticket, status: str) -> Ticket:
        ticket.status = status
        self.db.flush()
        return ticket

    def list_by_order(self, order_no: str) -> list[Ticket]:
        return (
            self.db.query(Ticket)
            .filter(Ticket.order_no == order_no)
            .order_by(Ticket.ticket_no)
            .all()
        )

    def has_active_ticket(self, passenger_id: str, instance_id: str) -> bool:
        tickets = self.list_for_passenger_instance_for_update(passenger_id, instance_id)
        return any(ticket.status == "有效" for ticket in tickets)

    def list_for_passenger_instance_for_update(
        self,
        passenger_id: str,
        instance_id: str,
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .where(
                Ticket.passenger_id == passenger_id,
                Ticket.instance_id == instance_id,
            )
            .with_for_update()
        )
        return list(self.db.execute(stmt).scalars().all())

    def next_ticket_sequence(self) -> int:
        prefix = f"T{date.today():%Y%m%d}"
        ticket_no = self.db.execute(
            text(
                """
                SELECT ticket_no
                FROM ticket
                WHERE ticket_no LIKE :prefix
                ORDER BY ticket_no DESC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {"prefix": f"{prefix}%"},
        ).scalar_one_or_none()
        if not ticket_no:
            return 1
        return int(str(ticket_no)[-9:]) + 1


class RefundChangeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        ticket_no: str,
        op_type: str,
        fee: Decimal,
        new_ticket_no: str | None,
        price_diff: Decimal,
        op_time: datetime,
    ) -> RefundChange:
        record = RefundChange(
            ticket_no=ticket_no,
            op_type=op_type,
            fee=fee,
            new_ticket_no=new_ticket_no,
            price_diff=price_diff,
            op_time=op_time,
        )
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def list_by_user(
        self,
        user_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        params = {
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        total = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM refund_change rc
                JOIN ticket t ON rc.ticket_no = t.ticket_no
                JOIN aptorder o ON t.order_no = o.order_no
                WHERE o.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()
        rows = self.db.execute(
            text(
                """
                SELECT
                    rc.refund_id,
                    rc.ticket_no,
                    rc.op_type,
                    rc.fee,
                    rc.new_ticket_no,
                    rc.price_diff,
                    rc.op_time
                FROM refund_change rc
                JOIN ticket t ON rc.ticket_no = t.ticket_no
                JOIN aptorder o ON t.order_no = o.order_no
                WHERE o.user_id = :user_id
                ORDER BY rc.op_time DESC, rc.refund_id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows], int(total)
