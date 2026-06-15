from dataclasses import dataclass
from typing import Any

from study_podcast.domain.errors import DomainError
from study_podcast.infrastructure.runtime_settings import (
    apply_settings_values,
    available_engines,
    serialize_settings_values,
)


@dataclass
class RuntimeSettingsTransaction:
    container: object

    def update(self, values: dict[str, Any]) -> None:
        self._validate_visible_engine(values)
        serialized = serialize_settings_values(values)
        self.container.settings_repo.save_many(serialized)
        self.container.env_writer.write(values)
        apply_settings_values(self.container.settings, serialized)
        self.container.reload_required = True
        if self.container.runtime_status in {"idle", "ready"}:
            self.container.runtime_status = "reload_pending"

    def reload(self) -> None:
        self.container.rebuild_runtime()

    def _validate_visible_engine(self, values: dict[str, Any]) -> None:
        engine = values.get("active_tts_engine")
        if engine is None:
            return
        if engine == "fake" and "fake" not in available_engines(self.container.settings):
            raise DomainError("development TTS engine is disabled")
