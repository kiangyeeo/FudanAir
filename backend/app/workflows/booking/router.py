from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.deps import get_db
from app.workflows.booking.schemas import BookingRequest, BookingResponse, PayResponse
from app.workflows.booking.service import BookingService


router = APIRouter(tags=["booking"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: BookingRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return BookingService(db).create_order(user_id, payload)


@router.post("/{order_no}/pay", response_model=PayResponse)
def pay_order(
    order_no: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return BookingService(db).pay_order(user_id, order_no)


@router.post("/{order_no}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(
    order_no: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    BookingService(db).cancel_order(user_id, order_no)
