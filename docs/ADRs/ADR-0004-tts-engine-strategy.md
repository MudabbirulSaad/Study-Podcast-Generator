# ADR-0004: TTS Engine Strategy

## Decision
Use Chatterbox as the production-style local TTS engine and keep the deterministic fake TTS engine as explicit dev/test infrastructure only.

## Consequences
Normal tests do not need GPU, model downloads, or Chatterbox because they opt into the fake engine. User-facing settings hide the fake engine unless `ENABLE_DEV_TTS_ENGINE=true`. Future adapters can target Kokoro and MOSS-TTSD through the same `TtsEngine` port.
