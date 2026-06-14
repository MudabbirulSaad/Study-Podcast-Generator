# ADR-0005: Local Persistence Strategy

## Decision
Use SQLite for metadata and filesystem storage for scripts/audio under a configured storage root.

## Consequences
The app stays local-first and portable. Storage safety requires generated IDs, path traversal rejection, temp writes, and atomic renames.
