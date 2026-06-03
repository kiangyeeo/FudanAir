from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class AirlineCreate(BaseModel):
    iata_code: str = Field(..., min_length=2, max_length=2)
    airline_name: str = Field(..., min_length=1, max_length=128)

    model_config = {"str_strip_whitespace": True}


class AirlineUpdate(BaseModel):
    iata_code: str | None = Field(default=None, min_length=2, max_length=2)
    airline_name: str = Field(..., min_length=1, max_length=128)

    model_config = {"str_strip_whitespace": True}


class AirlineResponse(BaseModel):
    iata_code: str
    airline_name: str

    model_config = {"from_attributes": True}


class AircraftTypeCreate(BaseModel):
    model: str = Field(..., min_length=1, max_length=32)
    economy_seats: int = Field(..., ge=0)
    first_seats: int = Field(..., ge=0)

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_total_seats(self) -> AircraftTypeCreate:
        if self.economy_seats + self.first_seats <= 0:
            raise ValueError("机型座位总数必须大于0")
        return self


class AircraftTypeUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=32)
    economy_seats: int = Field(..., ge=0)
    first_seats: int = Field(..., ge=0)

    model_config = {"str_strip_whitespace": True}

    @model_validator(mode="after")
    def validate_total_seats(self) -> AircraftTypeUpdate:
        if self.economy_seats + self.first_seats <= 0:
            raise ValueError("机型座位总数必须大于0")
        return self


class AircraftTypeResponse(BaseModel):
    model: str
    economy_seats: int
    first_seats: int

    model_config = {"from_attributes": True}
