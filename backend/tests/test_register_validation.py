from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _assert_register_message(payload: dict[str, str], expected: str) -> None:
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": expected,
    }


def test_register_validation_reports_missing_name() -> None:
    _assert_register_message(
        {"name": "", "password": "abc123", "phone": "13800138000"},
        "Please enter your name",
    )


def test_register_validation_reports_short_password() -> None:
    _assert_register_message(
        {"name": "张三", "password": "12345", "phone": "13800138000"},
        "Password must be at least six characters.",
    )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"name": "", "password": "", "phone": "13800138000"}, "Please enter name, password"),
        ({"name": "", "password": "abc123", "phone": ""}, "Please enter name, phone number"),
        ({"name": "张三", "password": "", "phone": ""}, "Please enter password, phone number"),
    ],
)
def test_register_validation_reports_multiple_missing_fields(
    payload: dict[str, str],
    expected: str,
) -> None:
    _assert_register_message(payload, expected)
