from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import transaction
from app.core.exceptions import (
    AppException,
    InsufficientStockError,
    InstanceNotBookableError,
    ResourceInUseError,
    ResourceNotFoundError,
)
from app.core.id_generator import gen_instance_id
from app.domains.flight.models import CabinPrice, Flight, FlightInstance
from app.domains.flight.pricing import default_cabin_price_specs
from app.domains.flight.repository import (
    CabinPriceRepository,
    FlightInstanceRepository,
    FlightRepository,
)
from app.domains.flight.schemas import (
    CabinPriceReplace,
    FlightCreate,
    FlightInstanceBatchCreate,
    FlightInstanceCreate,
    FlightInstanceStatusUpdate,
    FlightUpdate,
)


INSTANCE_STATUS_PLANNED = "计划"
INSTANCE_STATUS_BOOKABLE = "可订"
ALLOWED_INSTANCE_STATUSES = {"计划", "可订", "已起飞", "已到达", "已取消"}
BOOKABLE_INSTANCE_STATUSES = {INSTANCE_STATUS_BOOKABLE}
CABIN_CLASS_ECONOMY = "经济舱"
CABIN_CLASS_FIRST = "头等舱"


class FlightService:
    def __init__(self, db: Session):
        self.db = db
        self.flight_repo = FlightRepository(db)
        self.instance_repo = FlightInstanceRepository(db)
        self.cabin_repo = CabinPriceRepository(db)

    def list_flights(
        self,
        page: int,
        page_size: int,
        airline_code: str | None = None,
        dep_airport_code: str | None = None,
        arr_airport_code: str | None = None,
    ) -> dict[str, object]:
        items, total = self.flight_repo.list_page(
            page,
            page_size,
            _optional_airline_code(airline_code),
            _optional_airport_code(dep_airport_code),
            _optional_airport_code(arr_airport_code),
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_flight_detail(self, flight_no: str) -> dict[str, object]:
        flight = self.get_flight_or_404(flight_no)
        return self._flight_detail(flight)

    def get_flight_or_404(self, flight_no: str) -> Flight:
        number = _flight_no(flight_no)
        flight = self.flight_repo.get(number)
        if not flight:
            raise ResourceNotFoundError(f"航班 {number} 不存在")
        return flight

    def create_flight(self, payload: FlightCreate) -> Flight:
        data = self._flight_data(payload)
        weekdays = _unique_weekdays(payload.weekdays)
        stopovers = _airport_codes(payload.stopovers)
        self._validate_route(data["dep_airport_code"], data["arr_airport_code"])
        self._validate_stopovers(
            data["dep_airport_code"],
            data["arr_airport_code"],
            stopovers,
        )
        try:
            with transaction(self.db):
                if self.flight_repo.get(data["flight_no"]):
                    raise AppException(f"航班 {data['flight_no']} 已存在")
                self._ensure_reference_data(data, stopovers)
                flight = self.flight_repo.create(**data)
                self.flight_repo.replace_weekdays(flight.flight_no, weekdays)
                self.flight_repo.replace_stopovers(flight.flight_no, stopovers)
                return flight
        except IntegrityError as exc:
            raise AppException(f"航班 {data['flight_no']} 创建失败") from exc

    def update_flight(self, flight_no: str, payload: FlightUpdate) -> Flight:
        number = _flight_no(flight_no)
        data = self._flight_data(payload, flight_no=number)
        weekdays = _unique_weekdays(payload.weekdays)
        stopovers = _airport_codes(payload.stopovers)
        self._validate_route(data["dep_airport_code"], data["arr_airport_code"])
        self._validate_stopovers(
            data["dep_airport_code"],
            data["arr_airport_code"],
            stopovers,
        )
        try:
            with transaction(self.db):
                flight = self.flight_repo.get(number)
                if not flight:
                    raise ResourceNotFoundError(f"航班 {number} 不存在")
                self._ensure_reference_data(data, stopovers)
                update_data = dict(data)
                update_data.pop("flight_no", None)
                flight = self.flight_repo.update(flight, **update_data)
                self.flight_repo.replace_weekdays(number, weekdays)
                self.flight_repo.replace_stopovers(number, stopovers)
                return flight
        except IntegrityError as exc:
            raise AppException(f"航班 {number} 更新失败") from exc

    def delete_flight(self, flight_no: str) -> None:
        number = _flight_no(flight_no)
        try:
            with transaction(self.db):
                flight = self.flight_repo.get(number)
                if not flight:
                    raise ResourceNotFoundError(f"航班 {number} 不存在")
                if self.flight_repo.has_instances(number):
                    raise ResourceInUseError(f"航班 {number} 已生成实例,无法删除")
                self.flight_repo.delete(flight)
        except IntegrityError as exc:
            raise ResourceInUseError(f"航班 {number} 被引用,无法删除") from exc

    def list_instances(
        self,
        page: int,
        page_size: int,
        flight_no: str | None = None,
        flight_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        normalized_status = _optional_status(status)
        items, total = self.instance_repo.list_page(
            page,
            page_size,
            _optional_flight_no(flight_no),
            flight_date,
            normalized_status,
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_instance_detail(self, instance_id: str) -> dict[str, object]:
        instance = self.get_instance_or_404(instance_id)
        return self._instance_detail(instance.instance_id)

    def get_instance_or_404(self, instance_id: str) -> FlightInstance:
        instance = self.instance_repo.get(instance_id)
        if not instance:
            raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
        return instance

    def ensure_instance_bookable(self, instance_id: str) -> FlightInstance:
        instance = self.get_instance_or_404(instance_id)
        self._ensure_instance_bookable(instance)
        return instance

    def create_instance(
        self,
        flight_no: str | FlightInstanceCreate,
        flight_date: date | None = None,
    ) -> FlightInstance:
        if isinstance(flight_no, FlightInstanceCreate):
            payload = flight_no
            number = _flight_no(payload.flight_no)
            instance_date = payload.flight_date
        else:
            number = _flight_no(flight_no)
            if flight_date is None:
                raise AppException("航班日期不能为空")
            instance_date = flight_date

        try:
            with transaction(self.db):
                existing = self.instance_repo.get_by_flight_date(number, instance_date)
                if existing:
                    return existing
                flight = self.flight_repo.get(number)
                if not flight:
                    raise ResourceNotFoundError(f"航班 {number} 不存在")
                self._ensure_date_in_weekday(number, instance_date)
                seats = self.flight_repo.get_aircraft_seats(number)
                if not seats:
                    raise ResourceNotFoundError(f"机型 {flight.aircraft_model} 不存在")
                economy_seats, first_seats = seats
                instance = self.instance_repo.create(
                    gen_instance_id(number, instance_date),
                    number,
                    instance_date,
                    economy_seats,
                    first_seats,
                    INSTANCE_STATUS_PLANNED,
                )
                specs = default_cabin_price_specs(
                    economy_seats,
                    first_seats,
                    flight.scheduled_departure,
                    flight.scheduled_arrival,
                )
                for spec in specs:
                    self.cabin_repo.create(
                        instance.instance_id,
                        spec.cabin_class,
                        spec.fare_type,
                        spec.price,
                        spec.available_seats,
                    )
                return instance
        except IntegrityError as exc:
            self.db.rollback()
            existing = self.instance_repo.get_by_flight_date(number, instance_date)
            if existing:
                return existing
            raise AppException(f"航班 {number} 实例创建失败") from exc

    def batch_generate_instances(
        self,
        flight_no: str | FlightInstanceBatchCreate,
        start: date | None = None,
        end: date | None = None,
    ) -> list[FlightInstance]:
        if isinstance(flight_no, FlightInstanceBatchCreate):
            payload = flight_no
            number = _flight_no(payload.flight_no)
            start_date = payload.start_date
            end_date = payload.end_date
        else:
            number = _flight_no(flight_no)
            if start is None or end is None:
                raise AppException("开始日期和结束日期不能为空")
            start_date = start
            end_date = end
        if end_date < start_date:
            raise AppException("结束日期不能早于开始日期")

        self.get_flight_or_404(number)
        weekdays = set(self.flight_repo.get_weekdays(number))
        created_or_existing: list[FlightInstance] = []
        current = start_date
        while current <= end_date:
            if current.isoweekday() in weekdays:
                created_or_existing.append(self.create_instance(number, current))
            current += timedelta(days=1)
        return created_or_existing

    def update_instance_status(
        self,
        instance_id: str,
        payload: FlightInstanceStatusUpdate | str,
    ) -> FlightInstance:
        status = payload.status if isinstance(payload, FlightInstanceStatusUpdate) else payload
        normalized_status = _status(status)
        try:
            with transaction(self.db):
                instance = self.instance_repo.get(instance_id)
                if not instance:
                    raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
                return self.instance_repo.update_status(instance, normalized_status)
        except IntegrityError as exc:
            raise AppException(f"航班实例 {instance_id} 状态更新失败") from exc

    def delete_instance(self, instance_id: str) -> None:
        try:
            with transaction(self.db):
                instance = self.instance_repo.get(instance_id)
                if not instance:
                    raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
                if self.instance_repo.has_tickets(instance_id):
                    raise ResourceInUseError(f"航班实例 {instance_id} 已有关联客票")
                self.instance_repo.delete(instance)
        except IntegrityError as exc:
            raise ResourceInUseError(f"航班实例 {instance_id} 被引用,无法删除") from exc

    def list_cabin_prices(self, instance_id: str) -> list[CabinPrice]:
        self.get_instance_or_404(instance_id)
        return self.cabin_repo.list_by_instance(instance_id)

    def set_cabin_prices(
        self,
        instance_id: str,
        payload: CabinPriceReplace,
    ) -> list[CabinPrice]:
        rows = [item.model_dump() for item in payload.cabin_prices]
        self._validate_cabin_price_rows(rows)
        try:
            with transaction(self.db):
                if not self.instance_repo.get(instance_id):
                    raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
                cabin_prices = self.cabin_repo.replace_all(instance_id, rows)
                totals = self.cabin_repo.sum_by_cabin(instance_id)
                self.instance_repo.set_seat_summary(
                    instance_id,
                    totals.get(CABIN_CLASS_ECONOMY, 0),
                    totals.get(CABIN_CLASS_FIRST, 0),
                )
                return cabin_prices
        except IntegrityError as exc:
            raise ResourceInUseError(f"航班实例 {instance_id} 的部分票价档位已有客票引用,无法删除") from exc

    def deduct_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int = 1,
    ) -> CabinPrice:
        self._validate_quantity(quantity)
        cabin = _cabin_class(cabin_class)
        fare = _fare_type(fare_type)
        try:
            with transaction(self.db):
                instance = self.instance_repo.get(instance_id)
                if not instance:
                    raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
                self._ensure_instance_bookable(instance)
                cabin_price = self.cabin_repo.lock(instance_id, cabin, fare)
                if not cabin_price:
                    raise ResourceNotFoundError("舱位价格档位不存在")
                available = int(cabin_price.available_seats)
                if available < quantity:
                    raise InsufficientStockError(f"剩余 {available},申请 {quantity}")
                self.cabin_repo.update_available(cabin_price, -quantity)
                if not self.instance_repo.adjust_seats(instance_id, cabin, -quantity):
                    raise InsufficientStockError("汇总库存不足")
                return cabin_price
        except IntegrityError as exc:
            raise InsufficientStockError("库存扣减失败") from exc

    def restore_seat(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int = 1,
    ) -> CabinPrice:
        self._validate_quantity(quantity)
        cabin = _cabin_class(cabin_class)
        fare = _fare_type(fare_type)
        try:
            with transaction(self.db):
                if not self.instance_repo.get(instance_id):
                    raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
                cabin_price = self.cabin_repo.lock(instance_id, cabin, fare)
                if not cabin_price:
                    raise ResourceNotFoundError("舱位价格档位不存在")
                self.cabin_repo.update_available(cabin_price, quantity)
                if not self.instance_repo.adjust_seats(instance_id, cabin, quantity):
                    raise AppException("汇总库存回补失败")
                return cabin_price
        except IntegrityError as exc:
            raise AppException("库存回补失败") from exc

    def lock_and_deduct_cabin(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int = 1,
    ) -> CabinPrice:
        return self.deduct_seat(instance_id, cabin_class, fare_type, quantity)

    def restore_cabin_stock(
        self,
        instance_id: str,
        cabin_class: str,
        fare_type: str,
        quantity: int = 1,
    ) -> CabinPrice:
        return self.restore_seat(instance_id, cabin_class, fare_type, quantity)

    def _flight_detail(self, flight: Flight) -> dict[str, object]:
        return {
            "flight_no": flight.flight_no,
            "scheduled_departure": flight.scheduled_departure,
            "scheduled_arrival": flight.scheduled_arrival,
            "fuel_infra_fee": float(flight.fuel_infra_fee),
            "dep_airport_code": flight.dep_airport_code,
            "dep_terminal": flight.dep_terminal,
            "arr_airport_code": flight.arr_airport_code,
            "arr_terminal": flight.arr_terminal,
            "airline_code": flight.airline_code,
            "airline_name": self.flight_repo.get_airline_name(flight.airline_code),
            "aircraft_model": flight.aircraft_model,
            "weekdays": self.flight_repo.get_weekdays(flight.flight_no),
            "stopovers": self.flight_repo.get_stopovers(flight.flight_no),
        }

    def _instance_detail(self, instance_id: str) -> dict[str, object]:
        context = self.instance_repo.detail_context(instance_id)
        if not context:
            raise ResourceNotFoundError(f"航班实例 {instance_id} 不存在")
        context["fuel_infra_fee"] = float(context["fuel_infra_fee"])
        context["cabin_prices"] = self.cabin_repo.list_by_instance(instance_id)
        return context

    def _flight_data(
        self,
        payload: FlightCreate | FlightUpdate,
        flight_no: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "scheduled_departure": payload.scheduled_departure,
            "scheduled_arrival": payload.scheduled_arrival,
            "fuel_infra_fee": payload.fuel_infra_fee,
            "dep_airport_code": _airport_code(payload.dep_airport_code),
            "dep_terminal": _optional_text(payload.dep_terminal),
            "arr_airport_code": _airport_code(payload.arr_airport_code),
            "arr_terminal": _optional_text(payload.arr_terminal),
            "airline_code": _airline_code(payload.airline_code),
            "aircraft_model": _aircraft_model(payload.aircraft_model),
        }
        if flight_no is not None:
            data["flight_no"] = flight_no
        elif isinstance(payload, FlightCreate):
            data["flight_no"] = _flight_no(payload.flight_no)
        return data

    def _ensure_reference_data(
        self,
        flight_data: dict[str, Any],
        stopovers: list[str],
    ) -> None:
        dep = flight_data["dep_airport_code"]
        arr = flight_data["arr_airport_code"]
        airline = flight_data["airline_code"]
        aircraft = flight_data["aircraft_model"]
        missing_airports = [
            code
            for code in [dep, arr, *stopovers]
            if not self.flight_repo.exists_airport(code)
        ]
        if missing_airports:
            raise ResourceNotFoundError(f"机场 {missing_airports[0]} 不存在")
        if not self.flight_repo.exists_airline(airline):
            raise ResourceNotFoundError(f"航司 {airline} 不存在")
        if not self.flight_repo.exists_aircraft_type(aircraft):
            raise ResourceNotFoundError(f"机型 {aircraft} 不存在")

    def _ensure_date_in_weekday(self, flight_no: str, flight_date: date) -> None:
        weekdays = self.flight_repo.get_weekdays(flight_no)
        if flight_date.isoweekday() not in weekdays:
            raise AppException("日期不在飞行日内")

    @staticmethod
    def _validate_route(dep_airport_code: str, arr_airport_code: str) -> None:
        if dep_airport_code == arr_airport_code:
            raise AppException("起降不能同机场")

    @staticmethod
    def _validate_stopovers(
        dep_airport_code: str,
        arr_airport_code: str,
        stopovers: list[str],
    ) -> None:
        if len(stopovers) != len(set(stopovers)):
            raise AppException("经停机场不能重复")
        if dep_airport_code in stopovers or arr_airport_code in stopovers:
            raise AppException("经停机场冲突")

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if quantity <= 0:
            raise AppException("座位数量必须大于0")

    def _ensure_instance_bookable(self, instance: FlightInstance) -> None:
        if instance.status not in BOOKABLE_INSTANCE_STATUSES:
            raise InstanceNotBookableError(f"航班实例 {instance.instance_id} 当前不可订")
        flight = self.flight_repo.get(instance.flight_no)
        if not flight:
            raise ResourceNotFoundError(f"航班 {instance.flight_no} 不存在")
        if _departure_at(instance.flight_date, flight.scheduled_departure) <= datetime.now():
            raise InstanceNotBookableError(f"航班实例 {instance.instance_id} 已起飞,不可订")

    @staticmethod
    def _validate_cabin_price_rows(rows: list[dict[str, Any]]) -> None:
        keys = [(row["cabin_class"], row["fare_type"]) for row in rows]
        if len(keys) != len(set(keys)):
            raise AppException("舱位定价档位不能重复")


def _flight_no(value: str) -> str:
    return value.strip().upper()


def _optional_flight_no(value: str | None) -> str | None:
    return _flight_no(value) if value else None


def _airport_code(value: str) -> str:
    return value.strip().upper()


def _optional_airport_code(value: str | None) -> str | None:
    return _airport_code(value) if value else None


def _airline_code(value: str) -> str:
    return value.strip().upper()


def _optional_airline_code(value: str | None) -> str | None:
    return _airline_code(value) if value else None


def _aircraft_model(value: str) -> str:
    return value.strip().upper()


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _airport_codes(values: list[str]) -> list[str]:
    return [_airport_code(value) for value in values]


def _unique_weekdays(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise AppException("飞行日不能重复")
    return sorted(values)


def _status(value: str) -> str:
    normalized = value.strip()
    if normalized == "延误":
        raise AppException("航班实例状态不允许为延误")
    if normalized not in ALLOWED_INSTANCE_STATUSES:
        raise AppException("航班实例状态不合法")
    return normalized


def _optional_status(value: str | None) -> str | None:
    return _status(value) if value else None


def _departure_at(flight_date: date, scheduled_departure: Any) -> datetime:
    if isinstance(scheduled_departure, timedelta):
        return datetime.combine(flight_date, time.min) + scheduled_departure
    if isinstance(scheduled_departure, str):
        scheduled_departure = time.fromisoformat(scheduled_departure)
    return datetime.combine(flight_date, scheduled_departure)


def _cabin_class(value: str) -> str:
    normalized = value.strip()
    if normalized not in {CABIN_CLASS_ECONOMY, CABIN_CLASS_FIRST}:
        raise AppException("舱位不合法")
    return normalized


def _fare_type(value: str) -> str:
    normalized = value.strip()
    if normalized not in {"标准", "特价"}:
        raise AppException("票价类型不合法")
    return normalized
