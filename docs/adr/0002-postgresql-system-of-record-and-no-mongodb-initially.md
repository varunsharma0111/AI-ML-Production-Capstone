# ADR 0002: PostgreSQL is the initial system of record

**Status:** Accepted
**Date:** 2026-08-30

## Context

Core data has strong relationships and integrity needs: memberships, permissions, tasks, jobs, audits, model versions, approvals, and events. Some model/evaluation metadata is flexible.

## Decision

Use PostgreSQL for transactional data and bounded JSONB metadata. Do not introduce MongoDB initially.

## Consequences

Foreign keys, transactions, migrations, and outbox writes preserve core correctness while JSONB covers controlled metadata variation. MongoDB may be proposed later only with measured document volume/query patterns that PostgreSQL cannot serve suitably.
