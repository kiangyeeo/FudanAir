from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pymysql
from sqlalchemy.engine import make_url
from tqdm import tqdm


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.security import hash_password
from scripts import generate_data, load_csv


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
ADMIN_ACCOUNTS = (
    ("A001", "admin123", "系统管理员"),
)


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
            progress = tqdm(total=5, desc="初始化数据库", unit="step")
            _recreate_database(cur, config["database"])
            progress.update()
            _execute_schema(cur)
            progress.update()
            counts = _load_initial_data(cur)
            progress.update(3)
            progress.close()
        conn.commit()
    except Exception:
        if "progress" in locals():
            progress.close()
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
    statements = _split_sql(SCHEMA_PATH.read_text(encoding="utf-8"))
    for statement in tqdm(statements, desc="执行 schema", unit="stmt"):
        cur.execute(statement)


def _split_sql(script: str) -> list[str]:
    return [
        statement.strip()
        for statement in script.split(";")
        if statement.strip()
    ]


def _load_initial_data(cur: Any) -> dict[str, int]:
    counts = load_csv.load_all(cur)
    counts["flight_instance"] = generate_data.generate_flight_instances(cur)
    counts["cabin_price"] = generate_data.generate_cabin_prices(cur)
    counts["admin"] = _create_admins(cur)
    return counts


def _create_admins(cur: Any) -> int:
    params = [
        (admin_id, hash_password(password), admin_name)
        for admin_id, password, admin_name in ADMIN_ACCOUNTS
    ]
    cur.executemany(
        """
        INSERT INTO admin (admin_id, admin_password, admin_name)
        VALUES (%s, %s, %s)
        """,
        params,
    )
    return len(params)


def _print_summary(counts: dict[str, int]) -> None:
    print("数据库初始化完成:")
    for table_name, count in counts.items():
        print(f"- {table_name}: {count}")


if __name__ == "__main__":
    main()
