from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorEnvelope:
    code: str
    message: str
    details: dict[str, object] | None = None
