from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domains.admin.repository import AdminRepository


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminRepository(db)

    def get_dashboard(self) -> dict[str, Any]:
        return self.repo.get_dashboard()
