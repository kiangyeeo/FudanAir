from __future__ import annotations

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import (
    AppException,
    InconsistentAirportCityError,
    ResourceInUseError,
    ResourceNotFoundError,
)
from app.domains.city.models import Airport, City, CityNearApt
from app.domains.city.repository import (
    AirportRepository,
    CityNearAirportRepository,
    CityRepository,
)
from app.domains.city.schemas import (
    AirportCreate,
    AirportUpdate,
    CityCreate,
    CityUpdate,
    NearAirportCreate,
)


ZERO_DISTANCE = Decimal("0.00")


class CityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CityRepository(db)

    def list_all(self) -> list[str]:
        return self.repo.list_names()

    def get_or_404(self, city_name: str) -> City:
        city = self.repo.get(city_name)
        if not city:
            raise ResourceNotFoundError(f"City {city_name} does not exist")
        return city

    def create(self, payload: CityCreate) -> City:
        try:
            with transaction(self.db):
                if self.repo.get(payload.city_name):
                    raise AppException(f"City {payload.city_name} already exists")
                return self.repo.create(payload.city_name)
        except IntegrityError as exc:
            raise AppException(f"City {payload.city_name} already exists") from exc

    def update(self, city_name: str, payload: CityUpdate) -> City:
        if city_name == payload.city_name:
            return self.get_or_404(city_name)
        try:
            with transaction(self.db):
                if not self.repo.get(city_name):
                    raise ResourceNotFoundError(f"City {city_name} does not exist")
                if self.repo.get(payload.city_name):
                    raise AppException(f"City {payload.city_name} already exists")
                return self.repo.rename(city_name, payload.city_name)
        except IntegrityError as exc:
            raise AppException(f"Failed to rename city {city_name}") from exc

    def delete(self, city_name: str) -> None:
        try:
            with transaction(self.db):
                city = self.repo.get(city_name)
                if not city:
                    raise ResourceNotFoundError(f"City {city_name} does not exist")
                if self.repo.has_airport(city_name):
                    raise ResourceInUseError(f"City {city_name} still has airports and cannot be deleted")
                self.repo.delete(city)
        except IntegrityError as exc:
            raise ResourceInUseError(f"City {city_name} is in use and cannot be deleted") from exc


class AirportService:
    def __init__(self, db: Session):
        self.db = db
        self.city_repo = CityRepository(db)
        self.airport_repo = AirportRepository(db)
        self.near_repo = CityNearAirportRepository(db)

    def list_all(self, city_name: str | None = None) -> list[Airport]:
        return self.airport_repo.list_all(city_name)

    def get_or_404(self, iata_code: str) -> Airport:
        code = _airport_code(iata_code)
        airport = self.airport_repo.get(code)
        if not airport:
            raise ResourceNotFoundError(f"Airport {code} does not exist")
        return airport

    def create(self, payload: AirportCreate) -> Airport:
        code = _airport_code(payload.iata_code)
        try:
            with transaction(self.db):
                if self.airport_repo.get(code):
                    raise AppException(f"Airport {code} already exists")
                self._ensure_city(payload.city_name)
                airport = self.airport_repo.create(
                    code,
                    payload.airport_name,
                    payload.city_name,
                )
                self.near_repo.upsert(payload.city_name, code, ZERO_DISTANCE)
                return airport
        except IntegrityError as exc:
            raise AppException(f"Failed to create airport {code}") from exc

    def update(self, iata_code: str, payload: AirportUpdate) -> Airport:
        code = _airport_code(iata_code)
        new_code = _airport_code(payload.iata_code) if payload.iata_code else code
        try:
            with transaction(self.db):
                airport = self.airport_repo.get(code)
                if not airport:
                    raise ResourceNotFoundError(f"Airport {code} does not exist")
                self._ensure_city(payload.city_name)
                old_city = str(airport.city_name)
                airport = self._save_update(airport, code, new_code, payload)
                self._sync_own_near_relation(old_city, payload.city_name, code, new_code)
                return airport
        except IntegrityError as exc:
            raise AppException(f"Failed to update airport {code}") from exc

    def delete(self, iata_code: str) -> None:
        code = _airport_code(iata_code)
        try:
            with transaction(self.db):
                airport = self.airport_repo.get(code)
                if not airport:
                    raise ResourceNotFoundError(f"Airport {code} does not exist")
                if self.airport_repo.is_referenced(code):
                    raise ResourceInUseError(f"Airport {code} is referenced by flights and cannot be deleted")
                self.airport_repo.delete(airport)
        except IntegrityError as exc:
            raise ResourceInUseError(f"Airport {code} is in use and cannot be deleted") from exc

    def _ensure_city(self, city_name: str) -> City:
        city = self.city_repo.get(city_name)
        if not city:
            raise ResourceNotFoundError(f"City {city_name} does not exist")
        return city

    def _save_update(
        self,
        airport: Airport,
        old_code: str,
        new_code: str,
        payload: AirportUpdate,
    ) -> Airport:
        if new_code == old_code:
            self._ensure_identity_editable(airport, old_code, new_code, payload)
            return self.airport_repo.update(
                airport,
                payload.airport_name,
                payload.city_name,
            )
        self._ensure_identity_editable(airport, old_code, new_code, payload)
        if self.airport_repo.get(new_code):
            raise AppException(f"Airport {new_code} already exists")
        return self.airport_repo.rename_code(
            airport,
            new_code,
            payload.airport_name,
            payload.city_name,
        )

    def _ensure_identity_editable(
        self,
        airport: Airport,
        old_code: str,
        new_code: str,
        payload: AirportUpdate,
    ) -> None:
        identity_changed = new_code != old_code or airport.airport_name != payload.airport_name
        if identity_changed and self.airport_repo.is_referenced(old_code):
            raise ResourceInUseError(f"Airport {old_code} is in use and its IATA code or name cannot be changed")

    def _sync_own_near_relation(
        self,
        old_city: str,
        new_city: str,
        old_code: str,
        new_code: str,
    ) -> None:
        if old_city != new_city:
            self.near_repo.delete_own_relation(old_city, new_code)
            self.near_repo.upsert(new_city, new_code, ZERO_DISTANCE)
        elif old_code != new_code:
            self.near_repo.upsert(new_city, new_code, ZERO_DISTANCE)


class CityNearAirportService:
    def __init__(self, db: Session):
        self.db = db
        self.city_repo = CityRepository(db)
        self.airport_repo = AirportRepository(db)
        self.near_repo = CityNearAirportRepository(db)

    def list_by_city(self, city_name: str) -> list[dict[str, object]]:
        self._ensure_city(city_name)
        return self.near_repo.list_by_city(city_name)

    def create(self, city_name: str, payload: NearAirportCreate) -> CityNearApt:
        code = _airport_code(payload.iata_code)
        try:
            with transaction(self.db):
                self._ensure_city(city_name)
                airport = self._ensure_airport(code)
                if self.near_repo.get(city_name, code):
                    raise AppException(f"City {city_name} and airport {code} relation already exists")
                self._validate_zero_distance(city_name, airport, payload.distance)
                return self.near_repo.create(city_name, code, payload.distance)
        except IntegrityError as exc:
            raise AppException(f"Failed to create nearby airport relation {city_name}-{code}") from exc

    def delete(self, city_name: str, iata_code: str) -> None:
        code = _airport_code(iata_code)
        try:
            with transaction(self.db):
                relation = self.near_repo.get(city_name, code)
                if not relation:
                    raise ResourceNotFoundError(f"Nearby airport relation {city_name}-{code} does not exist")
                airport = self._ensure_airport(code)
                if relation.distance == ZERO_DISTANCE and airport.city_name == city_name:
                    raise InconsistentAirportCityError()
                self.near_repo.delete(relation)
        except IntegrityError as exc:
            raise AppException(f"Failed to delete nearby airport relation {city_name}-{code}") from exc

    def _ensure_city(self, city_name: str) -> City:
        city = self.city_repo.get(city_name)
        if not city:
            raise ResourceNotFoundError(f"City {city_name} does not exist")
        return city

    def _ensure_airport(self, iata_code: str) -> Airport:
        airport = self.airport_repo.get(iata_code)
        if not airport:
            raise ResourceNotFoundError(f"Airport {iata_code} does not exist")
        return airport

    @staticmethod
    def _validate_zero_distance(
        city_name: str,
        airport: Airport,
        distance: Decimal,
    ) -> None:
        if distance == ZERO_DISTANCE and airport.city_name != city_name:
            raise InconsistentAirportCityError()


def _airport_code(iata_code: str) -> str:
    return iata_code.strip().upper()
