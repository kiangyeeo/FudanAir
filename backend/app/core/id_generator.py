from __future__ import annotations

import secrets
import string
from datetime import date, datetime


_ORDER_SUFFIX_ALPHABET = string.ascii_uppercase + string.digits


def gen_order_no() -> str:
    suffix = "".join(secrets.choice(_ORDER_SUFFIX_ALPHABET) for _ in range(6))
    return f"O{datetime.now():%Y%m%d%H%M%S}{suffix}"


def gen_ticket_no(seq: int) -> str:
    return f"T{date.today():%Y%m%d}{seq:09d}"


def gen_instance_id(flight_no: str, flight_date: date) -> str:
    return f"{flight_no}_{flight_date:%Y%m%d}"
