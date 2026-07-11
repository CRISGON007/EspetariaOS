from __future__ import annotations

import os
import platform
import shutil
import socket
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


START_TIME = time.time()


def _temperature() -> float | None:
    try:
        temperatures = psutil.sensors_temperatures()
        for entries in temperatures.values():
            for entry in entries:
                if entry.current is not None:
                    return round(float(entry.current), 1)
    except Exception:
        return None
    return None


def _local_ips() -> list[str]:
    values: list[str] = []
    try:
        for addresses in psutil.net_if_addrs().values():
            for address in addresses:
                if address.family == socket.AF_INET and not address.address.startswith("127."):
                    values.append(address.address)
    except Exception:
        pass
    return sorted(set(values))


def system_info(database_path: str, version: str) -> dict[str, Any]:
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(Path(database_path).resolve().parent)
    boot = datetime.fromtimestamp(psutil.boot_time()).isoformat()
    return {
        "version": version,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "architecture": platform.machine(),
        "ips": _local_ips(),
        "cpuPercent": psutil.cpu_percent(interval=0.15),
        "cpuCount": psutil.cpu_count(logical=True),
        "memory": {
            "total": memory.total,
            "used": memory.used,
            "available": memory.available,
            "percent": memory.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": round((disk.used / disk.total) * 100, 1) if disk.total else 0,
        },
        "temperatureC": _temperature(),
        "systemBootAt": boot,
        "serviceUptimeSeconds": int(time.time() - START_TIME),
        "databasePath": str(Path(database_path).resolve()),
        "databaseSize": Path(database_path).stat().st_size if Path(database_path).exists() else 0,
    }


def create_backup(database_path: str, backups_dir: str) -> Path:
    source = Path(database_path)
    if not source.exists():
        raise FileNotFoundError("Banco de dados não encontrado.")
    destination_dir = Path(backups_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = destination_dir / f"espetaria_{timestamp}.db"

    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    return destination


def list_backups(backups_dir: str) -> list[dict[str, Any]]:
    directory = Path(backups_dir)
    directory.mkdir(parents=True, exist_ok=True)
    files = sorted(directory.glob("espetaria_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "name": file.name,
            "size": file.stat().st_size,
            "createdAt": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
        }
        for file in files[:50]
    ]


def safe_backup_path(backups_dir: str, name: str) -> Path:
    if Path(name).name != name or not name.startswith("espetaria_") or not name.endswith(".db"):
        raise ValueError("Nome de backup inválido.")
    path = Path(backups_dir) / name
    if not path.exists():
        raise FileNotFoundError("Backup não encontrado.")
    return path


def backup_created_today(backups_dir: str) -> bool:
    directory = Path(backups_dir)
    if not directory.exists():
        return False
    today = datetime.now().date()
    return any(
        datetime.fromtimestamp(file.stat().st_mtime).date() == today
        for file in directory.glob("espetaria_*.db")
    )

def create_daily_backup_if_needed(database_path: str, backups_dir: str) -> Path | None:
    if backup_created_today(backups_dir):
        return None
    return create_backup(database_path, backups_dir)


def prune_old_backups(backups_dir: str, keep: int = 30) -> list[str]:
    directory = Path(backups_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe_keep = max(1, keep)
    files = sorted(directory.glob("espetaria_*.db"), key=lambda file: file.stat().st_mtime, reverse=True)
    removed: list[str] = []
    for file in files[safe_keep:]:
        file.unlink(missing_ok=True)
        removed.append(file.name)
    return removed
