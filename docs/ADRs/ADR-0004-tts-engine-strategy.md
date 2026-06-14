# ADR-0004: TTS Engine Strategy

## Decision
Use a deterministic fake TTS engine by default and add Chatterbox as an optional lazy-loaded adapter.

## Consequences
Normal tests do not need GPU, model downloads, or Chatterbox. Future adapters can target Kokoro and MOSS-TTSD through the same `TtsEngine` port.
