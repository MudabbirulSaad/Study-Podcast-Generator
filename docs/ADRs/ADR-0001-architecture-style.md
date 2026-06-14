# ADR-0001: Architecture Style

## Decision
Use strict hexagonal architecture for the backend.

## Consequences
Domain and application layers remain testable without FastAPI, SQLite, filesystem, or TTS libraries. Lightweight architecture tests enforce import boundaries.
