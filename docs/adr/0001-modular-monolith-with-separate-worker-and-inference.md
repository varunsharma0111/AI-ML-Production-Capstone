# ADR 0001: Start with a modular monolith

**Status:** Accepted
**Date:** 2026-08-30

## Context

The platform needs cohesive identity, task, job, model-registry, agent-governance, and audit workflows, but also needs long-running work and model-serving workloads that scale differently.

## Decision

Build one FastAPI modular monolith for the public API and core business domains. Deploy worker and model-inference processes independently. Use explicit module interfaces and domain events so extraction remains possible when justified.

## Consequences

The team avoids early distributed transactions, network failure modes, and deployment overhead. Worker and inference capacity can scale separately. Future extraction requires stable contracts, observability, and evidence of independent ownership, scaling, or isolation needs.
