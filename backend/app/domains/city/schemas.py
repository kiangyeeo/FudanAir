from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import NEARBY_DISTANCE_MAX_KM


MAX_NEARBY_DISTANCE = Decimal(str(NEARBY_DISTANCE_MAX_KM))


class CityCreate(BaseModel):
    city_name: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class CityUpdate(CityCreate):
    pass


class CityResponse(BaseModel):
    city_name: str

    model_config = {"from_attributes": True}


class AirportCreate(BaseModel):
    iata_code: str = Field(..., min_length=3, max_length=3)
    airport_name: str = Field(..., min_length=1, max_length=128)
    city_name: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class AirportUpdate(BaseModel):
    airport_name: str = Field(..., min_length=1, max_length=128)
    city_name: str = Field(..., min_length=1, max_length=32)

    model_config = {"str_strip_whitespace": True}


class AirportResponse(BaseModel):
    iata_code: str
    airport_name: str
    city_name: str

    model_config = {"from_attributes": True}


class NearAirportCreate(BaseModel):
    iata_code: str = Field(..., min_length=3, max_length=3)
    distance: Decimal = Field(..., ge=Decimal("0"), le=MAX_NEARBY_DISTANCE)

    model_config = {"str_strip_whitespace": True}


class NearAirportResponse(BaseModel):
    iata_code: str
    airport_name: str
    distance: float
