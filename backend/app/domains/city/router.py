from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.deps import get_db
from app.domains.city.schemas import (
    AirportCreate,
    AirportResponse,
    AirportUpdate,
    CityCreate,
    CityResponse,
    CityUpdate,
    NearAirportCreate,
    NearAirportResponse,
)
from app.domains.city.service import (
    AirportService,
    CityNearAirportService,
    CityService,
)


city_router = APIRouter(prefix="/cities", tags=["city"])
airport_router = APIRouter(prefix="/airports", tags=["airport"])
router = city_router


@city_router.get("", response_model=list[str])
def list_cities(db: Session = Depends(get_db)) -> list[str]:
    return CityService(db).list_all()


@city_router.post(
    "",
    response_model=CityResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_city(
    payload: CityCreate,
    db: Session = Depends(get_db),
) -> CityResponse:
    return CityService(db).create(payload)


@city_router.put(
    "/{city_name}",
    response_model=CityResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_city(
    city_name: str,
    payload: CityUpdate,
    db: Session = Depends(get_db),
) -> CityResponse:
    return CityService(db).update(city_name, payload)


@city_router.delete(
    "/{city_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_city(city_name: str, db: Session = Depends(get_db)) -> None:
    CityService(db).delete(city_name)


@city_router.get(
    "/{city_name}/near-airports",
    response_model=list[NearAirportResponse],
)
def list_near_airports(
    city_name: str,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return CityNearAirportService(db).list_by_city(city_name)


@city_router.post(
    "/{city_name}/near-airports",
    response_model=NearAirportResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_near_airport(
    city_name: str,
    payload: NearAirportCreate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    relation = CityNearAirportService(db).create(city_name, payload)
    airport = AirportService(db).get_or_404(relation.iata_code)
    return {
        "iata_code": relation.iata_code,
        "airport_name": airport.airport_name,
        "distance": float(relation.distance),
    }


@city_router.delete(
    "/{city_name}/near-airports/{iata_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_near_airport(
    city_name: str,
    iata_code: str,
    db: Session = Depends(get_db),
) -> None:
    CityNearAirportService(db).delete(city_name, iata_code)


@airport_router.get("", response_model=list[AirportResponse])
def list_airports(
    city: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AirportResponse]:
    return AirportService(db).list_all(city)


@airport_router.get("/{iata_code}", response_model=AirportResponse)
def get_airport(iata_code: str, db: Session = Depends(get_db)) -> AirportResponse:
    return AirportService(db).get_or_404(iata_code)


@airport_router.post(
    "",
    response_model=AirportResponse,
    dependencies=[Depends(get_current_admin)],
)
def create_airport(
    payload: AirportCreate,
    db: Session = Depends(get_db),
) -> AirportResponse:
    return AirportService(db).create(payload)


@airport_router.put(
    "/{iata_code}",
    response_model=AirportResponse,
    dependencies=[Depends(get_current_admin)],
)
def update_airport(
    iata_code: str,
    payload: AirportUpdate,
    db: Session = Depends(get_db),
) -> AirportResponse:
    return AirportService(db).update(iata_code, payload)


@airport_router.delete(
    "/{iata_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
def delete_airport(iata_code: str, db: Session = Depends(get_db)) -> None:
    AirportService(db).delete(iata_code)
