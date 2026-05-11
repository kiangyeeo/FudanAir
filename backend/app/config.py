from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    DB_URL: str = "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/fudan_air?charset=utf8mb4"
    JWT_SECRET: str = "please-change-me-to-a-random-string-at-least-32-chars"
    JWT_EXPIRE_MINUTES: int = 1440
    ORDER_EXPIRE_MINUTES: int = 15
    SCHEDULER_INTERVAL_SECONDS: int = 60
    INSTANCE_GENERATION_HOUR: int = 3
    INSTANCE_AHEAD_DAYS: int = 90
    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]


settings = Settings()
