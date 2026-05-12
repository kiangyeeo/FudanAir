from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.deps import get_db
from app.domains.admin.schemas import DashboardResponse
from app.domains.admin.service import AdminService


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(get_current_admin)],
)
def get_dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    return AdminService(db).get_dashboard()
