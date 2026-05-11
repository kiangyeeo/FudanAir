from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.deps import get_db
from app.domains.flight.schemas import (
    CabinPriceReplace,
    CabinPriceResponse,
    FlightCreate,
    FlightDetailResponse,
    FlightInstanceBatchCreate,
    FlightInstanceCreate,
    FlightInstanceDetailResponse,
    FlightInstanceListResponse,
    FlightInstancePageResponse,
    FlightInstanceStatusUpdate,
    FlightPageResponse,
    FlightUpdate,
)
from app.domains.flight.service import FlightService


flight_router = APIRouter(prefix="/flights", tags=["flight"])
flight_instance_router = APIRouter(prefix="/flight-instances", tags=["flight-instance"])
router = flight_router


@flight_router.get("", response_model=FlightPageResponse)
def list_flights(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    airline: str | None = Query(default=None),
    dep_airport: str | None = Query(default=None),
    arr_airport: str | None = Query(default=None),
    airline_code: str | None = Query(default=None),
    dep_airport_code: str | None = Query(default=None),
    arr_airport_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return FlightService(db).list_flights(
        page,
        page_size,
        airline_code or airline,
        dep_airport_code or dep_airport,
        arr_airport_code or arr_airport,
    )


@flight_router.get("/{flight_no}", response_model=FlightDetailResponse)
def get_flight(flight_no: str, db: Session = Depends(get_db)) -> dict[str, object]:
    return FlightService(db).get_flight_detail(flight_no)


@flight_router.post(
    "",
    response_model=FlightDetailResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_flight(
    payload: FlightCreate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = FlightService(db)
    flight = service.create_flight(payload)
    return service.get_flight_detail(flight.flight_no)


@flight_router.put(
    "/{flight_no}",
    response_model=FlightDetailResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_flight(
    flight_no: str,
    payload: FlightUpdate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = FlightService(db)
    flight = service.update_flight(flight_no, payload)
    return service.get_flight_detail(flight.flight_no)


@flight_router.delete(
    "/{flight_no}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_flight(flight_no: str, db: Session = Depends(get_db)) -> None:
    FlightService(db).delete_flight(flight_no)


@flight_instance_router.get("", response_model=FlightInstancePageResponse)
def list_instances(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    flight_no: str | None = Query(default=None),
    flight_date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return FlightService(db).list_instances(
        page,
        page_size,
        flight_no,
        flight_date,
        status,
    )


@flight_instance_router.post(
    "",
    response_model=FlightInstanceDetailResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_instance(
    payload: FlightInstanceCreate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = FlightService(db)
    instance = service.create_instance(payload)
    return service.get_instance_detail(instance.instance_id)


@flight_instance_router.post(
    "/batch-generate",
    response_model=list[FlightInstanceListResponse],
    dependencies=[Depends(get_current_admin)],
)
def batch_generate_instances(
    payload: FlightInstanceBatchCreate,
    db: Session = Depends(get_db),
) -> list[FlightInstanceListResponse]:
    return FlightService(db).batch_generate_instances(payload)


@flight_instance_router.get(
    "/{instance_id}",
    response_model=FlightInstanceDetailResponse,
)
def get_instance(instance_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    return FlightService(db).get_instance_detail(instance_id)


@flight_instance_router.patch(
    "/{instance_id}/status",
    response_model=FlightInstanceDetailResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_instance_status(
    instance_id: str,
    payload: FlightInstanceStatusUpdate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = FlightService(db)
    instance = service.update_instance_status(instance_id, payload)
    return service.get_instance_detail(instance.instance_id)


@flight_instance_router.delete(
    "/{instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_instance(instance_id: str, db: Session = Depends(get_db)) -> None:
    FlightService(db).delete_instance(instance_id)


@flight_instance_router.get(
    "/{instance_id}/cabin-prices",
    response_model=list[CabinPriceResponse],
)
def list_cabin_prices(
    instance_id: str,
    db: Session = Depends(get_db),
) -> list[CabinPriceResponse]:
    return FlightService(db).list_cabin_prices(instance_id)


@flight_instance_router.put(
    "/{instance_id}/cabin-prices",
    response_model=list[CabinPriceResponse],
    dependencies=[Depends(get_current_admin)],
)
def replace_cabin_prices(
    instance_id: str,
    payload: CabinPriceReplace,
    db: Session = Depends(get_db),
) -> list[CabinPriceResponse]:
    return FlightService(db).set_cabin_prices(instance_id, payload)
