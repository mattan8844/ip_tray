import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

UPDATE_INTERVAL_OPTIONS = (0.5, 1.0, 2.0, 5.0)
PUBLIC_REFRESH_OPTIONS = (15.0, 30.0, 60.0, 120.0)
REQUEST_TIMEOUT_OPTIONS = (2.0, 3.5, 5.0, 8.0)


@dataclass
class RuntimeConfig:
    update_interval: float = 1.0
    public_refresh_interval: float = 30.0
    request_timeout: float = 3.5
    notifications_enabled: bool = False


def default_config_path() -> Path:
    return Path.home() / "Library" / "Application Support" / "IPTray" / "config.json"


def _coerce_option(value: Any, options: tuple[float, ...], fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    if numeric in options:
        return numeric
    return fallback


def _from_raw(raw: dict[str, Any]) -> RuntimeConfig:
    return RuntimeConfig(
        update_interval=_coerce_option(raw.get("update_interval"), UPDATE_INTERVAL_OPTIONS, 1.0),
        public_refresh_interval=_coerce_option(raw.get("public_refresh_interval"), PUBLIC_REFRESH_OPTIONS, 30.0),
        request_timeout=_coerce_option(raw.get("request_timeout"), REQUEST_TIMEOUT_OPTIONS, 3.5),
        notifications_enabled=bool(raw.get("notifications_enabled", False)),
    )


def load_runtime_config(path: Path | None = None) -> RuntimeConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return RuntimeConfig()

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load config from %s: %s", config_path, exc)
        return RuntimeConfig()

    if not isinstance(payload, dict):
        logger.warning("Config payload is not an object: %s", config_path)
        return RuntimeConfig()

    return _from_raw(payload)


def save_runtime_config(config: RuntimeConfig, path: Path | None = None) -> None:
    config_path = path or default_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to save config to %s: %s", config_path, exc)
