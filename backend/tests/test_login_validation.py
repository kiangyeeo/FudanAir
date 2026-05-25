from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.auth.schemas import LoginRequest
from app.auth.service import AuthService
from app.core.exceptions import AuthenticationError, InvalidPhoneFormatError
from app.core.security import hash_password
from app.main import app


client = TestClient(app)


def _assert_login_validation_message(payload: dict[str, str], expected: str) -> None:
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "code": "VALIDATION_ERROR",
        "message": expected,
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"phone": "", "password": "abc123"}, "请输入手机号"),
        ({"phone": "13800138000", "password": ""}, "请输入密码"),
        ({"phone": "", "password": ""}, "请输入手机号,密码"),
    ],
)
def test_login_validation_reports_missing_fields(
    payload: dict[str, str],
    expected: str,
) -> None:
    _assert_login_validation_message(payload, expected)


def test_login_api_reports_invalid_phone_format() -> None:
    response = client.post(
        "/api/auth/login",
        json={"phone": "1234567890", "password": "abc123"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "INVALID_PHONE_FORMAT",
        "message": "手机号格式错误",
    }


def test_login_rejects_invalid_phone_format() -> None:
    service = AuthService.__new__(AuthService)
    payload = LoginRequest(phone="1234567890", password="abc123")

    with pytest.raises(InvalidPhoneFormatError, match="手机号格式错误"):
        service.login(payload)


def test_login_reports_unregistered_user() -> None:
    service = AuthService.__new__(AuthService)
    service._get_user_by_phone = lambda _phone: None
    payload = LoginRequest(phone="13800138000", password="abc123")

    with pytest.raises(AuthenticationError, match="用户暂未注册"):
        service.login(payload)


def test_login_reports_wrong_password() -> None:
    user = SimpleNamespace(user_password=hash_password("rightpass"))
    service = AuthService.__new__(AuthService)
    service._get_user_by_phone = lambda _phone: user
    payload = LoginRequest(phone="13800138000", password="wrongpass")

    with pytest.raises(AuthenticationError, match="密码错误，请重试"):
        service.login(payload)
