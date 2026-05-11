from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

from faker import Faker


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password


_FAKER = Faker("zh_CN")
_DEMO_USER_PASSWORD = "user123456"
_DEMO_PHONE_BASE = 13_900_000_000
_ID_CHECK_CODES = "0123456789X"


def create_admins(cur: Any) -> int:
    admins = [
        ("A001", "admin123", "系统管理员"),
        ("A002", "admin456", "运营管理员"),
    ]
    params = [
        (admin_id, hash_password(password), admin_name)
        for admin_id, password, admin_name in admins
    ]
    return _executemany(cur, _insert_admin_sql(), params)


def generate_demo_users(cur: Any, n: int = 20) -> int:
    if n <= 0:
        return 0
    params = [
        (hash_password(_DEMO_USER_PASSWORD), _FAKER.name(), _phone_for(index))
        for index in range(n)
    ]
    return _executemany(cur, _insert_user_sql(), params)


def generate_demo_passengers(cur: Any, n: int = 50) -> int:
    if n <= 0:
        return 0
    params = []
    used_id_numbers: set[str] = set()
    while len(params) < n:
        id_no, real_name, birth_date = _make_passenger()
        if id_no in used_id_numbers:
            continue
        used_id_numbers.add(id_no)
        params.append((id_no, real_name, birth_date))
    return _executemany(cur, _insert_passenger_sql(), params)


def _phone_for(index: int) -> str:
    return str(_DEMO_PHONE_BASE + index)


def _make_passenger() -> tuple[str, str, date]:
    birth_date = _FAKER.date_of_birth(minimum_age=18, maximum_age=75)
    area_code = _FAKER.random_int(min=110000, max=659999)
    sequence = _FAKER.random_int(min=1, max=999)
    check_code = _FAKER.random_element(elements=list(_ID_CHECK_CODES))
    id_no = f"{area_code:06d}{birth_date:%Y%m%d}{sequence:03d}{check_code}"
    return id_no, _FAKER.name(), birth_date


def _executemany(cur: Any, sql: str, params: list[tuple[Any, ...]]) -> int:
    if not params:
        return 0
    cur.executemany(sql, params)
    return int(cur.rowcount)


def _insert_admin_sql() -> str:
    return """
        INSERT INTO admin (admin_id, admin_password, admin_name)
        VALUES (%s, %s, %s)
    """


def _insert_user_sql() -> str:
    return """
        INSERT INTO user (user_password, name, phone)
        VALUES (%s, %s, %s)
    """


def _insert_passenger_sql() -> str:
    return """
        INSERT INTO passenger (id_no, real_name, birth_date)
        VALUES (%s, %s, %s)
    """
