from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.deps import get_db
from app.domains.ticket.schemas import RefundChangePageResponse
from app.domains.ticket.service import RefundChangeService
from app.workflows.refund.schemas import (
    CabinClass,
    ChangeTicketRequest,
    ChangeTicketResponse,
    FareType,
    RefundOperation,
    RefundQuoteResponse,
    RefundTicketRequest,
    RefundTicketResponse,
)
from app.workflows.refund.service import RefundService


router = APIRouter(tags=["refund"])


@router.get("/quote", response_model=RefundQuoteResponse, response_model_exclude_none=True)
def quote_refund_or_change(
    ticket_no: Annotated[str, Query(min_length=1, max_length=32)],
    op_type: RefundOperation,
    new_instance_id: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    new_cabin_class: CabinClass | None = None,
    new_fare_type: FareType | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return RefundService(db).quote(
        user_id,
        ticket_no,
        op_type,
        new_instance_id,
        new_cabin_class,
        new_fare_type,
    )


@router.post("/refund", response_model=RefundTicketResponse)
def refund_ticket(
    payload: RefundTicketRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return RefundService(db).refund_ticket(user_id, payload.ticket_no)


@router.post("/change", response_model=ChangeTicketResponse)
def change_ticket(
    payload: ChangeTicketRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return RefundService(db).change_ticket(
        user_id,
        payload.ticket_no,
        payload.new_instance_id,
        payload.new_cabin_class,
        payload.new_fare_type,
    )


@router.get("/records", response_model=RefundChangePageResponse)
def list_refund_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return RefundChangeService(db).list_by_user(user_id, page, page_size)
