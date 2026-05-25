from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


REGISTER_PASSWORD_MIN_LENGTH = 6


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=REGISTER_PASSWORD_MIN_LENGTH, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)

    model_config = {"str_strip_whitespace": True}


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class AdminLoginRequest(BaseModel):
    admin_id: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class UserRegisterResponse(BaseModel):
    user_id: int
    phone: str
    name: str


class UserSession(BaseModel):
    role: Literal["user"] = "user"
    user_id: int
    phone: str
    name: str


class AdminSession(BaseModel):
    role: Literal["admin"] = "admin"
    admin_id: str
    name: str
