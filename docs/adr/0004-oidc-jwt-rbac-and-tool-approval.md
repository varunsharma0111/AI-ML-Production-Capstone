# ADR 0004: OIDC identity, JWT verification, RBAC, and governed tools

**Status:** Accepted
**Date:** 2026-08-30

## Context

The platform needs delegated login and must prevent both users and AI agents from acting beyond authorized scope.

## Decision

Use an external OAuth/OIDC provider with Authorization Code + PKCE. Verify JWTs in the API and enforce server-side RBAC plus permissions and workspace ownership. Agent tools are typed, allowlisted APIs; consequential actions require explicit approval and all calls are audited.

## Consequences

The project avoids custom credential storage and makes AI authority explicit. It must define an identity-provider choice, permission matrix, approval UX, retention/redaction rules, and secure token/session handling before implementation.
