# ADR 0005: Evaluate and approve models before serving

**Status:** Accepted
**Date:** 2026-08-30

## Context

An ML model can be accurate in development while failing safety, latency, cost, or robustness requirements in operation.

## Decision

Version model artifacts and metadata. Require offline evaluation results and an authorized approval before promotion to an inference stage. Pin inference to an approved version and record the version for every prediction.

## Consequences

Deployments are traceable and reversible. The team must define the first ML use case, evaluation dataset, thresholds, artifact store, and approval authority before the ML phase.
