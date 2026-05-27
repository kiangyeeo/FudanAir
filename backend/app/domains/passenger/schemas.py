from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PassengerResponse(BaseModel):
    id_no: str
    real_name: str
    birth_date: date

    model_config = {"from_attributes": True}


class PassengerCreate(BaseModel):
    id_no: str = Field(..., min_length=1, max_length=32)
    real_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date

    model_config = {"str_strip_whitespace": True}


class PassengerUpdate(BaseModel):
    id_no: str | None = Field(default=None, min_length=1, max_length=32)
    real_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date

    model_config = {"str_strip_whitespace": True}
