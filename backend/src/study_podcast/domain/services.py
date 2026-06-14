import re

from study_podcast.domain.entities import SpeakerSegment, TextChunk
from study_podcast.domain.errors import DomainError

_SPEAKER_RE = re.compile(r"^\s*\[(?P<speaker>[A-Za-z0-9 _-]{1,40})\]\s*(?P<text>.*)$")


def detect_speaker_segments(script_text: str) -> list[SpeakerSegment]:
    segments: list[SpeakerSegment] = []
    current_speaker = "Narrator"
    current_lines: list[str] = []

    def flush() -> None:
        text = " ".join(line.strip() for line in current_lines if line.strip()).strip()
        if text:
            segments.append(SpeakerSegment(speaker=current_speaker, text=text))

    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _SPEAKER_RE.match(line)
        if match:
            flush()
            current_lines = []
            current_speaker = match.group("speaker").strip()
            tagged_text = match.group("text").strip()
            if tagged_text:
                current_lines.append(tagged_text)
        else:
            current_lines.append(line)

    flush()
    return segments


def split_script_into_chunks(
    script_text: str,
    *,
    max_chunk_chars: int,
    max_chunks: int,
) -> list[TextChunk]:
    if max_chunk_chars < 1:
        raise DomainError("max chunk size must be positive")

    chunks: list[TextChunk] = []
    for segment in detect_speaker_segments(script_text):
        chunks.extend(
            _split_segment(segment, start_index=len(chunks), max_chunk_chars=max_chunk_chars)
        )
        if len(chunks) > max_chunks:
            raise DomainError("script produces too many chunks")
    return chunks


def _split_segment(
    segment: SpeakerSegment,
    *,
    start_index: int,
    max_chunk_chars: int,
) -> list[TextChunk]:
    sentences = [
        piece.strip() for piece in re.split(r"(?<=[.!?])\s+", segment.text) if piece.strip()
    ]
    chunks: list[TextChunk] = []
    current = ""

    for sentence in sentences or [segment.text]:
        if len(sentence) > max_chunk_chars:
            pieces = _split_long_text(sentence, max_chunk_chars)
        else:
            pieces = [sentence]
        for piece in pieces:
            candidate = f"{current} {piece}".strip() if current else piece
            if current and len(candidate) > max_chunk_chars:
                chunks.append(TextChunk(start_index + len(chunks), segment.speaker, current))
                current = piece
            else:
                current = candidate

    if current:
        chunks.append(TextChunk(start_index + len(chunks), segment.speaker, current))
    return chunks


def _split_long_text(text: str, max_chunk_chars: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if current and len(candidate) > max_chunk_chars:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces
