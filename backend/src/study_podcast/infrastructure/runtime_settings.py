from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from study_podcast.domain.errors import DomainError
from study_podcast.infrastructure.config import Settings

EDITABLE_SETTINGS: tuple[str, ...] = (
    "active_tts_engine",
    "chatterbox_device",
    "max_script_size_bytes",
    "max_chunk_chars",
    "max_chunks",
    "chatterbox_max_concurrent_jobs",
    "audio_merge_max_concurrent_jobs",
    "max_active_jobs_total",
    "storage_root",
    "frontend_origin",
    "serve_frontend",
)

ENV_KEYS: dict[str, str] = {key: key.upper() for key in EDITABLE_SETTINGS}


def available_engines(settings: Settings) -> list[str]:
    engines = ["chatterbox"]
    if settings.enable_dev_tts_engine:
        engines.append("fake")
    return engines


def apply_settings_values(settings: Settings, values: dict[str, str]) -> None:
    for key, raw_value in values.items():
        if key not in EDITABLE_SETTINGS:
            continue
        current = getattr(settings, key)
        setattr(settings, key, _coerce_value(raw_value, current))


def apply_startup_overrides(settings: Settings, stored_values: dict[str, str]) -> None:
    env_file_values = parse_env_file(settings.env_file_path)
    merged: dict[str, str] = {}
    for key in EDITABLE_SETTINGS:
        env_key = ENV_KEYS[key]
        if key in stored_values:
            merged[key] = stored_values[key]
        if env_key in env_file_values:
            merged[key] = env_file_values[env_key]
        if env_key in os.environ:
            merged[key] = os.environ[env_key]
    apply_settings_values(settings, merged)


def serialize_settings_values(values: dict[str, Any]) -> dict[str, str]:
    serialized: dict[str, str] = {}
    for key, value in values.items():
        if key not in EDITABLE_SETTINGS:
            raise DomainError(f"setting is not editable: {key}")
        serialized[key] = _serialize_value(value)
    return serialized


def settings_snapshot(settings: Settings) -> dict[str, object]:
    return {key: getattr(settings, key) for key in EDITABLE_SETTINGS}


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass
class DotEnvFileWriter:
    path: Path

    def write(self, values: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing_lines = self.path.read_text().splitlines() if self.path.exists() else []
        updates = {ENV_KEYS[key]: _serialize_value(value) for key, value in values.items()}
        seen: set[str] = set()
        lines: list[str] = []
        for line in existing_lines:
            if "=" not in line or line.lstrip().startswith("#"):
                lines.append(line)
                continue
            key, _ = line.split("=", 1)
            env_key = key.strip()
            if env_key in updates:
                lines.append(f"{env_key}={updates[env_key]}")
                seen.add(env_key)
            else:
                lines.append(line)
        for env_key, value in updates.items():
            if env_key not in seen:
                lines.append(f"{env_key}={value}")
        self.path.write_text("\n".join(lines) + "\n")


def _serialize_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _coerce_value(raw_value: str, current: object) -> object:
    if isinstance(current, bool):
        return raw_value.lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int):
        return int(raw_value)
    if isinstance(current, Path):
        return Path(raw_value)
    return raw_value
