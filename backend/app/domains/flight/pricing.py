from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.core.constants import (
    DEFAULT_ECONOMY_SPECIAL_DISCOUNT,
    DEFAULT_FIRST_CLASS_MULTIPLIER,
    DEFAULT_PRICE_STEP,
    ECONOMY_STANDARD_RATIO,
)


_CENT = Decimal("0.01")


@dataclass(frozen=True)
class CabinPriceSpec:
    cabin_class: str
    fare_type: str
    price: Decimal
    available_seats: int


def default_cabin_price_specs(
    economy_seats: int,
    first_seats: int,
    base_price: Any,
) -> list[CabinPriceSpec]:
    """按航班裸票价派生各舱位档位定价与初始库存。

    base_price 即 flight.base_price(由 CSV / 管理员维护)的经济舱标准裸票价(不含燃油基建);
    经济舱特价、头等舱标准价均由其乘系数派生(系数见 core/constants.py)。
    """
    economy_standard, economy_special = split_economy_seats(economy_seats)
    standard_price, special_price, first_price = default_price_set(base_price)
    specs = [
        CabinPriceSpec("经济舱", "标准", standard_price, economy_standard),
        CabinPriceSpec("经济舱", "特价", special_price, economy_special),
    ]
    if first_seats > 0:
        specs.append(CabinPriceSpec("头等舱", "标准", first_price, first_seats))
    return specs


def split_economy_seats(total: int) -> tuple[int, int]:
    ratio = Decimal(str(ECONOMY_STANDARD_RATIO))
    standard = int((Decimal(total) * ratio).to_integral_value(rounding=ROUND_HALF_UP))
    standard = min(max(standard, 0), total)
    return standard, total - standard


def default_price_set(base_price: Any) -> tuple[Decimal, Decimal, Decimal]:
    """返回(经济舱标准价, 经济舱特价, 头等舱标准价)三元组, 均按价格步长取整。"""
    economy_price = _round_price(Decimal(str(base_price)))
    special_price = _round_price(economy_price * Decimal(DEFAULT_ECONOMY_SPECIAL_DISCOUNT))
    first_price = _round_price(economy_price * Decimal(DEFAULT_FIRST_CLASS_MULTIPLIER))
    return economy_price, special_price, first_price


def _round_price(value: Decimal) -> Decimal:
    price_step = Decimal(DEFAULT_PRICE_STEP)
    rounded = (value / price_step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (rounded * price_step).quantize(_CENT)
