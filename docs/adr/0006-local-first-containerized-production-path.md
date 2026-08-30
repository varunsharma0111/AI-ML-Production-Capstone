# ADR 0006: Local-first development with a production deployment path

**Status:** Accepted
**Date:** 2026-08-30

## Context

The capstone must be demonstrable on a developer machine while also proving production deployment practices.

## Decision

Develop and test locally using containers and service emulators where needed. Add Kubernetes/Helm and Terraform only in the production-delivery phase. CI/CD promotes versioned images through staging before production.

## Consequences

Early development remains accessible and fast. Production infrastructure remains declarative and repeatable, but requires a cloud/provider decision, budget, secret-management integration, and environment-specific operational runbooks.
