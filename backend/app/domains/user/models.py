from __future__ import annotations

from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import BIGINT

from app.core.database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_password = Column(String(255), nullable=False)
    name = Column(String(64), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
