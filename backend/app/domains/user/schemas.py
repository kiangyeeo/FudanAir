from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    user_id: int
    phone: str
    name: str

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=1, max_length=20)

    model_config = {"str_strip_whitespace": True}


class PasswordUpdate(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=32)
    new_password: str = Field(..., min_length=6, max_length=32)

    model_config = {"str_strip_whitespace": True}
