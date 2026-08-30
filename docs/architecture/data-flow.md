# Data Flows

## User request lifecycle

1. A user signs in and opens an authorized workspace.
2. The web app submits a validated REST command with correlation and idempotency identifiers.
3. The API authenticates, authorizes, persists a task or job, and returns either a synchronous result or `202 Accepted` with the job ID.
4. The UI displays state from REST and applies authorized WebSocket updates.
5. The authoritative terminal result remains queryable from PostgreSQL after the connection ends.

## Authentication flow

1. The browser starts OAuth/OIDC Authorization Code with PKCE against the configured identity provider.
2. The provider authenticates the user and returns an authorization response to the registered callback.
3. The application obtains an access token/session and sends credentials only over TLS.
4. FastAPI verifies JWT signature via issuer keys plus issuer, audience, expiry, and required claims.
5. The API resolves local workspace membership and permissions; token identity alone never grants resource access.

## API request flow

`Browser → API middleware → token validation → permission policy → request schema validation → domain service → transaction → response`.

Commands write state and outbox entries atomically. Queries use PostgreSQL or a validated cache-aside read path. External calls, inference, and tools never run inside an open database transaction.

## Database flow

The API begins a short transaction, enforces workspace/resource scope, updates domain tables, appends immutable audit records, and writes an outbox event when integration is required. Constraints protect invariants. The transaction commits before an event publisher, worker, or remote call acts. Read replicas are not an initial requirement.

## Cache flow

For eligible read models, the API looks up a namespaced Redis key. A hit is returned only if its TTL and authorization scope are valid. On a miss, PostgreSQL is read and a TTL-bound representation is stored. A domain write invalidates relevant keys after commit. Redis is never the sole record of durable jobs, permissions, or user content.

## Event/message flow

After commit, the outbox publisher serializes a versioned event to Kafka. Each event includes its ID, type/version, occurred time, correlation ID, actor/workspace scope, and minimal payload. Consumers persist processed event IDs or use idempotent writes before acknowledging. Transient delivery failure retries; poison messages are routed to a dead-letter topic with alerting and a replay procedure.

## Worker flow

1. API creates a durable job with status `queued` and queues its identifier.
2. A worker claims the identifier, moves the job to `running`, and records an attempt.
3. It executes a bounded handler with timeout, idempotency, progress updates, and trace propagation.
4. It writes a terminal status, result reference, error category, audit record, and outbox event.
5. Retryable failures back off; exhausted failures enter a reviewable dead-letter state.

## ML inference flow

The worker or API calls inference only after input validation and quota/permission checks. The inference service resolves the explicitly requested or currently approved model version, validates the model input contract, executes prediction, and returns output with model/version, latency, and request metadata. The caller persists a result reference and emits completion. Sensitive inputs/outputs are redacted or minimized in telemetry.

## AI agent/tool flow

1. A user starts an agent task within a workspace and allowed capability scope.
2. The orchestrator builds minimal context and declares permitted typed tools.
3. For each proposed tool call it validates input schema, RBAC permission, ownership scope, rate/cost budget, and policy.
4. Read-only approved calls execute; consequential calls wait for a recorded human approval.
5. Outcomes are returned to the model, persisted as a traceable run, and surfaced as job updates. Repeated/tool-loop limits terminate unsafe or unproductive runs.

## WebSocket notification flow

The browser authenticates the WebSocket handshake and requests only permissible channels. The API tracks connection-to-user/workspace mappings and fan-outs job events after authorization. Messages contain state changes and IDs rather than sensitive full payloads. Clients reconnect with exponential backoff then use REST to reconcile missed updates; ordering is handled through job version/timestamp rather than assumed transport delivery.
