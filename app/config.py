from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("ESPETARIA_HOST", "0.0.0.0")
    port: int = int(os.getenv("ESPETARIA_PORT", "8080"))
    database_path: str = os.getenv("ESPETARIA_DB", "data/espetaria.db")
    session_hours: int = int(os.getenv("ESPETARIA_SESSION_HOURS", "12"))
    environment: str = os.getenv("ESPETARIA_ENV", "production").lower()
    backups_dir: str = os.getenv("ESPETARIA_BACKUPS", "backups")
    logs_dir: str = os.getenv("ESPETARIA_LOGS", "logs")
    demo_mode: bool = os.getenv("ESPETARIA_DEMO", "false").lower() in {"1", "true", "yes", "on"}

    @property
    def development(self) -> bool:
        return self.environment == "development"


settings = Settings()
