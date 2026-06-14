# ADR-0002: Backend Stack

## Decision
Use Python, FastAPI, `uv`, FastAPI routers, and in-process workers for v1.

## Consequences
The API remains simple to run locally. External durable queues are deferred.
