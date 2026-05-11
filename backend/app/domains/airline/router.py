from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.deps import get_db
from app.domains.airline.schemas import (
    AircraftTypeCreate,
    AircraftTypeResponse,
    AircraftTypeUpdate,
    AirlineCreate,
    AirlineResponse,
    AirlineUpdate,
)
from app.domains.airline.service import AircraftTypeService, AirlineService


airline_router = APIRouter(prefix="/airlines", tags=["airline"])
aircraft_type_router = APIRouter(prefix="/aircraft-types", tags=["aircraft-type"])
router = airline_router


@airline_router.get("", response_model=list[AirlineResponse])
def list_airlines(db: Session = Depends(get_db)) -> list[AirlineResponse]:
    return AirlineService(db).list_all()


@airline_router.post(
    "",
    response_model=AirlineResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_airline(
    payload: AirlineCreate,
    db: Session = Depends(get_db),
) -> AirlineResponse:
    return AirlineService(db).create(payload)


@airline_router.put(
    "/{iata_code}",
    response_model=AirlineResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_airline(
    iata_code: str,
    payload: AirlineUpdate,
    db: Session = Depends(get_db),
) -> AirlineResponse:
    return AirlineService(db).update(iata_code, payload)


@airline_router.delete(
    "/{iata_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_airline(iata_code: str, db: Session = Depends(get_db)) -> None:
    AirlineService(db).delete(iata_code)


@aircraft_type_router.get("", response_model=list[AircraftTypeResponse])
def list_aircraft_types(
    db: Session = Depends(get_db),
) -> list[AircraftTypeResponse]:
    return AircraftTypeService(db).list_all()


@aircraft_type_router.post(
    "",
    response_model=AircraftTypeResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_aircraft_type(
    payload: AircraftTypeCreate,
    db: Session = Depends(get_db),
) -> AircraftTypeResponse:
    return AircraftTypeService(db).create(payload)


@aircraft_type_router.put(
    "/{model}",
    response_model=AircraftTypeResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_aircraft_type(
    model: str,
    payload: AircraftTypeUpdate,
    db: Session = Depends(get_db),
) -> AircraftTypeResponse:
    return AircraftTypeService(db).update(model, payload)


@aircraft_type_router.delete(
    "/{model}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_aircraft_type(model: str, db: Session = Depends(get_db)) -> None:
    AircraftTypeService(db).delete(model)
