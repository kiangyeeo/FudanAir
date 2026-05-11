from __future__ import annotations

from sqlalchemy import Column, String

from app.core.database import Base


class Admin(Base):
    __tablename__ = "admin"

    admin_id = Column(String(32), primary_key=True)
    admin_password = Column(String(255), nullable=False)
    admin_name = Column(String(64), nullable=False)
