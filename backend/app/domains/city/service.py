from __future__ import annotations

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
            raise ResourceNotFoundError(f"城市 {city_name} 不存在")
        return city

    def create(self, payload: CityCreate) -> City:
        try:
            with self.db.begin():
                if self.repo.get(payload.city_name):
                    raise AppException(f"城市 {payload.city_name} 已存在")
                return self.repo.create(payload.city_name)
        except IntegrityError as exc:
            raise AppException(f"城市 {payload.city_name} 已存在") from exc

    def update(self, city_name: str, payload: CityUpdate) -> City:
        if city_name == payload.city_name:
            return self.get_or_404(city_name)
        try:
            with self.db.begin():
                if not self.repo.get(city_name):
                    raise ResourceNotFoundError(f"城市 {city_name} 不存在")
                if self.repo.get(payload.city_name):
                    raise AppException(f"城市 {payload.city_name} 已存在")
                return self.repo.rename(city_name, payload.city_name)
        except IntegrityError as exc:
            raise AppException(f"城市 {city_name} 改名失败") from exc

    def delete(self, city_name: str) -> None:
        try:
            with self.db.begin():
                city = self.repo.get(city_name)
                if not city:
                    raise ResourceNotFoundError(f"城市 {city_name} 不存在")
                if self.repo.has_airport(city_name):
                    raise ResourceInUseError(f"城市 {city_name} 仍有机场引用")
                self.repo.delete(city)
        except IntegrityError as exc:
            raise ResourceInUseError(f"城市 {city_name} 被引用,无法删除") from exc


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
            raise ResourceNotFoundError(f"机场 {code} 不存在")
        return airport

    def create(self, payload: AirportCreate) -> Airport:
        code = _airport_code(payload.iata_code)
        try:
            with self.db.begin():
                if self.airport_repo.get(code):
                    raise AppException(f"机场 {code} 已存在")
                self._ensure_city(payload.city_name)
                airport = self.airport_repo.create(
                    code,
                    payload.airport_name,
                    payload.city_name,
                )
                self.near_repo.upsert(payload.city_name, code, ZERO_DISTANCE)
                return airport
        except IntegrityError as exc:
            raise AppException(f"机场 {code} 创建失败") from exc

    def update(self, iata_code: str, payload: AirportUpdate) -> Airport:
        code = _airport_code(iata_code)
        try:
            with self.db.begin():
                airport = self.airport_repo.get(code)
                if not airport:
                    raise ResourceNotFoundError(f"机场 {code} 不存在")
                self._ensure_city(payload.city_name)
                old_city = str(airport.city_name)
                airport = self.airport_repo.update(
                    airport,
                    payload.airport_name,
                    payload.city_name,
                )
                if old_city != payload.city_name:
                    self.near_repo.delete_own_relation(old_city, code)
                    self.near_repo.upsert(payload.city_name, code, ZERO_DISTANCE)
                return airport
        except IntegrityError as exc:
            raise AppException(f"机场 {code} 更新失败") from exc

    def delete(self, iata_code: str) -> None:
        code = _airport_code(iata_code)
        try:
            with self.db.begin():
                airport = self.airport_repo.get(code)
                if not airport:
                    raise ResourceNotFoundError(f"机场 {code} 不存在")
                if self.airport_repo.is_referenced(code):
                    raise ResourceInUseError(f"机场 {code} 被航班引用,无法删除")
                self.airport_repo.delete(airport)
        except IntegrityError as exc:
            raise ResourceInUseError(f"机场 {code} 被引用,无法删除") from exc

    def _ensure_city(self, city_name: str) -> City:
        city = self.city_repo.get(city_name)
        if not city:
            raise ResourceNotFoundError(f"城市 {city_name} 不存在")
        return city


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
            with self.db.begin():
                self._ensure_city(city_name)
                airport = self._ensure_airport(code)
                if self.near_repo.get(city_name, code):
                    raise AppException(f"城市 {city_name} 与机场 {code} 关系已存在")
                self._validate_zero_distance(city_name, airport, payload.distance)
                return self.near_repo.create(city_name, code, payload.distance)
        except IntegrityError as exc:
            raise AppException(f"临近机场关系 {city_name}-{code} 创建失败") from exc

    def delete(self, city_name: str, iata_code: str) -> None:
        code = _airport_code(iata_code)
        try:
            with self.db.begin():
                relation = self.near_repo.get(city_name, code)
                if not relation:
                    raise ResourceNotFoundError(f"临近机场关系 {city_name}-{code} 不存在")
                airport = self._ensure_airport(code)
                if relation.distance == ZERO_DISTANCE and airport.city_name == city_name:
                    raise InconsistentAirportCityError()
                self.near_repo.delete(relation)
        except IntegrityError as exc:
            raise AppException(f"临近机场关系 {city_name}-{code} 删除失败") from exc

    def _ensure_city(self, city_name: str) -> City:
        city = self.city_repo.get(city_name)
        if not city:
            raise ResourceNotFoundError(f"城市 {city_name} 不存在")
        return city

    def _ensure_airport(self, iata_code: str) -> Airport:
        airport = self.airport_repo.get(iata_code)
        if not airport:
            raise ResourceNotFoundError(f"机场 {iata_code} 不存在")
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
