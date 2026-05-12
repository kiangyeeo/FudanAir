from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.deps import get_db
from app.domains.passenger.schemas import PassengerResponse, PassengerUpdate
from app.domains.passenger.service import PassengerService


router = APIRouter(prefix="/passengers", tags=["passenger"])


@router.get("", response_model=list[PassengerResponse])
def list_passengers(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return PassengerService(db).list_by_user(user_id)


@router.put("/{id_no}", response_model=PassengerResponse)
def update_passenger(
    id_no: str,
    payload: PassengerUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PassengerResponse:
    return PassengerService(db).update(user_id, id_no, payload)
