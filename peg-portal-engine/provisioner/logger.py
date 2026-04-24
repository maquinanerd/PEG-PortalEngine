"""
Logger compartilhado do PEG Portal Engine.

- Console (stdout) + arquivo (logs/peg_{timestamp}.log)
- Nivel via .env (LOG_LEVEL), padrao INFO
- Helper para mascarar credenciais
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


_LOGGER_NAME = "peg"
_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False
_log_file_path: Optional[Path] = None


def _resolve_level(level_name: Optional[str]) -> int:
    if not level_name:
        return logging.INFO
    name = level_name.strip().upper()
    return getattr(logging, name, logging.INFO)


def _logs_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logger() -> logging.Logger:
    """Retorna o logger configurado (singleton, idempotente)."""
    global _initialized, _log_file_path

    logger = logging.getLogger(_LOGGER_NAME)

    if _initialized:
        return logger

    level = _resolve_level(os.getenv("LOG_LEVEL"))
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    try:
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(level)
        console.setFormatter(formatter)
        logger.addHandler(console)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"[logger] Falha ao registrar console handler: {exc}\n")

    # File handler
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _logs_dir() / f"peg_{timestamp}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        _log_file_path = log_path
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"[logger] Falha ao registrar file handler: {exc}\n")

    _initialized = True
    logger.debug("Logger inicializado (nivel=%s)", logging.getLevelName(level))
    return logger


def get_log_file_path() -> Optional[Path]:
    """Retorna o caminho do arquivo de log atual (se houver)."""
    return _log_file_path


def log_credencial_segura(_valor: object) -> str:
    """Sempre retorna a mascara — nunca exponha credenciais em logs."""
    return "****"
