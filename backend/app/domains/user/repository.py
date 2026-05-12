from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.user.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_phone(self, phone: str) -> User | None:
        return self.db.query(User).filter(User.phone == phone).one_or_none()

    def update_profile(
        self,
        user: User,
        name: str | None,
        phone: str | None,
    ) -> User:
        if name is not None:
            user.name = name
        if phone is not None:
            user.phone = phone
        self.db.flush()
        return user

    def update_password(self, user: User, password_hash: str) -> User:
        user.user_password = password_hash
        self.db.flush()
        return user
