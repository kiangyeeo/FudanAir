from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.exceptions import OldPasswordMismatchError, PhoneAlreadyExistsError
from app.core.security import hash_password, verify_password
from app.domains.passenger.service import PassengerService
from app.domains.user.schemas import PasswordUpdate, UserProfileUpdate
from app.domains.user.service import UserService


class FakeTransaction:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_args: object) -> None:
        return None


class FakeSession:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.info: dict[str, Any] = {}
        self.rows = rows or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def in_transaction(self) -> bool:
        return True

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def begin(self) -> FakeTransaction:
        return FakeTransaction()

    def execute(self, statement: Any, params: dict[str, Any]) -> "FakeResult":
        self.calls.append((str(statement), params))
        return FakeResult(self.rows)


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeUserRepository:
    def __init__(self, user: SimpleNamespace, existing_phone: SimpleNamespace | None = None) -> None:
        self.user = user
        self.existing_phone = existing_phone

    def get(self, _user_id: int) -> SimpleNamespace:
        return self.user

    def get_by_phone(self, _phone: str) -> SimpleNamespace | None:
        return self.existing_phone

    def update_profile(
        self,
        user: SimpleNamespace,
        name: str | None,
        phone: str | None,
    ) -> SimpleNamespace:
        if name is not None:
            user.name = name
        if phone is not None:
            user.phone = phone
        return user

    def update_password(self, user: SimpleNamespace, password_hash: str) -> SimpleNamespace:
        user.user_password = password_hash
        return user


def make_user_service(
    user: SimpleNamespace,
    existing_phone: SimpleNamespace | None = None,
) -> UserService:
    service = UserService.__new__(UserService)
    service.db = FakeSession()
    service.repo = FakeUserRepository(user, existing_phone)
    return service


def test_update_profile_changes_name_and_phone() -> None:
    user = SimpleNamespace(user_id=7, name="张三", phone="13800138000")
    service = make_user_service(user)
    payload = UserProfileUpdate(name="李四", phone="13900139000")

    updated = service.update_profile(7, payload)

    assert updated.name == "李四"
    assert updated.phone == "13900139000"


def test_update_profile_rejects_duplicate_phone() -> None:
    user = SimpleNamespace(user_id=7, name="张三", phone="13800138000")
    other_user = SimpleNamespace(user_id=8, name="李四", phone="13900139000")
    service = make_user_service(user, other_user)
    payload = UserProfileUpdate(name="张三", phone="13900139000")

    with pytest.raises(PhoneAlreadyExistsError):
        service.update_profile(7, payload)


def test_update_password_checks_old_password() -> None:
    user = SimpleNamespace(
        user_id=7,
        name="张三",
        phone="13800138000",
        user_password=hash_password("oldpass123"),
    )
    service = make_user_service(user)
    payload = PasswordUpdate(old_password="wrongpass", new_password="newpass789")

    with pytest.raises(OldPasswordMismatchError):
        service.update_password(7, payload)


def test_update_password_hashes_new_password() -> None:
    user = SimpleNamespace(
        user_id=7,
        name="张三",
        phone="13800138000",
        user_password=hash_password("oldpass123"),
    )
    service = make_user_service(user)
    payload = PasswordUpdate(old_password="oldpass123", new_password="newpass789")

    service.update_password(7, payload)

    assert verify_password("newpass789", user.user_password)


def test_passenger_list_by_user_joins_ticket_and_order() -> None:
    db = FakeSession(
        [
            {
                "id_no": "110101199001011234",
                "real_name": "张三",
                "birth_date": date(1990, 1, 1),
            }
        ]
    )

    passengers = PassengerService(db).list_by_user(7)

    sql, params = db.calls[0]
    assert "SELECT DISTINCT" in sql
    assert "JOIN ticket t ON t.passenger_id = p.id_no" in sql
    assert "JOIN aptorder o ON o.order_no = t.order_no" in sql
    assert "WHERE o.user_id = :user_id" in sql
    assert params == {"user_id": 7}
    assert passengers == [
        {
            "id_no": "110101199001011234",
            "real_name": "张三",
            "birth_date": date(1990, 1, 1),
        }
    ]
