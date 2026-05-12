from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_id
from app.deps import get_db
from app.domains.ticket.schemas import RefundChangePageResponse
from app.domains.ticket.service import RefundChangeService


router = APIRouter(tags=["refund"])


@router.get("/records", response_model=RefundChangePageResponse)
def list_refund_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return RefundChangeService(db).list_by_user(user_id, page, page_size)
