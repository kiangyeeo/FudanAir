from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.exceptions import OldPasswordMismatchError, PhoneAlreadyExistsError, ResourceNotFoundError
from app.core.security import hash_password, verify_password
from app.domains.passenger.schemas import PassengerCreate, PassengerUpdate
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


class FakePassengerRepository:
    def __init__(self) -> None:
        self.passengers: dict[str, SimpleNamespace] = {}
        self.bindings: set[tuple[int, str]] = set()

    def get(self, id_no: str) -> SimpleNamespace | None:
        return self.passengers.get(id_no)

    def create(self, id_no: str, real_name: str, birth_date: date) -> SimpleNamespace:
        passenger = SimpleNamespace(id_no=id_no, real_name=real_name, birth_date=birth_date)
        self.passengers[id_no] = passenger
        return passenger

    def update(self, passenger: SimpleNamespace, real_name: str, birth_date: date) -> SimpleNamespace:
        passenger.real_name = real_name
        passenger.birth_date = birth_date
        return passenger

    def bind_to_user(self, user_id: int, id_no: str) -> SimpleNamespace:
        self.bindings.add((user_id, id_no))
        return SimpleNamespace(user_id=user_id, id_no=id_no)

    def unbind_from_user(self, user_id: int, id_no: str) -> bool:
        binding = (user_id, id_no)
        if binding not in self.bindings:
            return False
        self.bindings.remove(binding)
        return True

    def belongs_to_user(self, user_id: int, id_no: str) -> bool:
        return (user_id, id_no) in self.bindings


def make_user_service(
    user: SimpleNamespace,
    existing_phone: SimpleNamespace | None = None,
) -> UserService:
    service = UserService.__new__(UserService)
    service.db = FakeSession()
    service.repo = FakeUserRepository(user, existing_phone)
    return service


def make_passenger_service(repo: FakePassengerRepository) -> PassengerService:
    service = PassengerService.__new__(PassengerService)
    service.db = FakeSession()
    service.repo = repo
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
    assert "FROM user_passenger up" in sql
    assert "JOIN passenger p ON p.id_no = up.id_no" in sql
    assert "WHERE up.user_id = :user_id" in sql
    assert params == {"user_id": 7}
    assert passengers == [
        {
            "id_no": "110101199001011234",
            "real_name": "张三",
            "birth_date": date(1990, 1, 1),
        }
    ]


def test_passenger_create_binds_to_current_user() -> None:
    repo = FakePassengerRepository()
    service = make_passenger_service(repo)
    payload = PassengerCreate(
        id_no="110101199001011234",
        real_name="张三",
        birth_date=date(1990, 1, 1),
    )

    passenger = service.create(7, payload)

    assert passenger.id_no == "110101199001011234"
    assert repo.bindings == {(7, "110101199001011234")}


def test_passenger_update_can_change_bound_id_without_touching_old_passenger() -> None:
    repo = FakePassengerRepository()
    repo.create("OLD", "张三", date(1990, 1, 1))
    repo.bind_to_user(7, "OLD")
    service = make_passenger_service(repo)
    payload = PassengerUpdate(
        id_no="NEW",
        real_name="李四",
        birth_date=date(1992, 2, 2),
    )

    passenger = service.update(7, "OLD", payload)

    assert passenger.id_no == "NEW"
    assert repo.bindings == {(7, "NEW")}
    assert repo.passengers["OLD"].real_name == "张三"


def test_passenger_delete_unbinds_only() -> None:
    repo = FakePassengerRepository()
    repo.create("P1", "张三", date(1990, 1, 1))
    repo.bind_to_user(7, "P1")
    service = make_passenger_service(repo)

    service.delete(7, "P1")

    assert repo.bindings == set()
    assert "P1" in repo.passengers


def test_passenger_delete_rejects_unbound_passenger() -> None:
    repo = FakePassengerRepository()
    service = make_passenger_service(repo)

    with pytest.raises(ResourceNotFoundError):
        service.delete(7, "P1")
