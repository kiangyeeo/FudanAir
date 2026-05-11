from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pymysql
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from scripts import generate_data, generate_demo, load_csv


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def main() -> None:
    config = _mysql_config()
    conn = pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        charset=config["charset"],
        autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            _recreate_database(cur, config["database"])
            _execute_schema(cur)
            counts = _load_initial_data(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _print_summary(counts)


def _mysql_config() -> dict[str, Any]:
    url = make_url(settings.DB_URL)
    if not url.database:
        raise ValueError("DB_URL 必须包含数据库名")
    return {
        "host": url.host or "localhost",
        "port": url.port or 3306,
        "user": url.username or "root",
        "password": url.password or "",
        "database": url.database,
        "charset": url.query.get("charset", "utf8mb4"),
    }


def _recreate_database(cur: Any, database: str) -> None:
    db_name = _quote_identifier(database)
    cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
    cur.execute(
        f"CREATE DATABASE {db_name} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE {db_name}")


def _quote_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):
        raise ValueError(f"数据库名仅允许字母、数字和下划线: {identifier}")
    return f"`{identifier}`"


def _execute_schema(cur: Any) -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"schema.sql 不存在: {SCHEMA_PATH}")
    for statement in _split_sql(SCHEMA_PATH.read_text(encoding="utf-8")):
        cur.execute(statement)


def _split_sql(script: str) -> list[str]:
    return [
        statement.strip()
        for statement in script.split(";")
        if statement.strip()
    ]


def _load_initial_data(cur: Any) -> dict[str, int]:
    counts = {
        "city": load_csv.load_cities(cur),
        "airport": load_csv.load_airports(cur),
        "city_near_apt": load_csv.load_city_near_apt(cur),
        "airline": load_csv.load_airlines(cur),
        "aircraft_type": load_csv.load_aircraft_types(cur),
        "flight": load_csv.load_flights(cur),
        "flight_weekday": load_csv.load_flight_weekdays(cur),
        "flight_stopover": load_csv.load_flight_stopovers(cur),
    }
    counts["flight_instance"] = generate_data.generate_flight_instances(cur)
    counts["cabin_price"] = generate_data.generate_cabin_prices(cur)
    counts["admin"] = generate_demo.create_admins(cur)
    counts["user"] = generate_demo.generate_demo_users(cur, n=20)
    counts["passenger"] = generate_demo.generate_demo_passengers(cur, n=50)
    return counts


def _print_summary(counts: dict[str, int]) -> None:
    print("数据库初始化完成:")
    for table_name, count in counts.items():
        print(f"- {table_name}: {count}")


if __name__ == "__main__":
    main()
