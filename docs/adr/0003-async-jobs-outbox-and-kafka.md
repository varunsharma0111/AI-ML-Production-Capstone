# ADR 0003: Durable jobs with transactional outbox; introduce Kafka by phase

**Status:** Accepted
**Date:** 2026-08-30

## Context

Long-running work must survive API restarts, and domain events must not be lost between committing database state and publishing a message. Kafka operation has non-trivial cost for a small project.

## Decision

Persist job intent in PostgreSQL before queueing work. Store outbox records in the same transaction as domain changes. Start with queue-based jobs and an outbox-compatible schema; add Kafka when durable replayable events and multiple consumers are implemented.

## Consequences

Job state remains recoverable and dual-write risk is controlled. Kafka remains purposeful rather than decorative. Consumers must be idempotent and operating procedures must handle dead letters and replay.
