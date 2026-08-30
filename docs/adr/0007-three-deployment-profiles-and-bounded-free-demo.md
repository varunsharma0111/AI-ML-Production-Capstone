# ADR 0007: Use three deployment profiles and keep the free demo bounded

**Status:** Accepted
**Date:** 2026-08-30

## Context

The capstone must be publicly demonstrable at $0 while retaining a credible production architecture. Free hosting plans have cold starts, resource limits, ephemeral disks, and no appropriate always-on worker or streaming guarantees.

## Decision

Maintain three profiles: a complete Docker Compose local stack; a free public demo comprising Vercel static web, one Render FastAPI web service, Neon PostgreSQL, and GitHub CI/CD; and a paid full-production target. The demo exposes only a bounded synchronous, database-backed vertical slice. It has no Kafka, Redis dependency, background worker, persistent queue, scheduler, or hosted ML inference service.

## Consequences

The public demo stays affordable and honest about its reliability limits, while local/Kubernetes demonstrations retain complete system coverage. Capability flags/configuration, REST reconciliation, stateless API design, and durable PostgreSQL state are required. Provider terms, identity provider, and eventual production cloud remain review points.
