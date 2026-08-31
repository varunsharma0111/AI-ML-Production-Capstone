# AuraML Security Architecture & Governance Model

---

## 1. Authentication & JWT Token Verification

AuraML delegates identity management to OIDC/OAuth2 providers. All protected API requests must present a valid Bearer JWT in the `Authorization` header:

```http
Authorization: Bearer <JWT_TOKEN>
```

- **JWKS Verification**: Public keys retrieved dynamically from `OIDC_JWKS_URL` and cached in memory.
- **Claims Enforcement**: Validates signature, expiration (`exp`), not-before (`nbf`), issuer (`iss`), and audience (`aud`).

---

## 2. Role-Based Access Control (RBAC)

Permission matrix enforced per workspace:

| Permission | Viewer | Editor | Owner |
|---|:---:|:---:|:---:|
| `DATASET_READ` | ✅ | ✅ | ✅ |
| `DATASET_CREATE` | ❌ | ✅ | ✅ |
| `MODEL_READ` | ✅ | ✅ | ✅ |
| `MODEL_TRAIN` | ❌ | ✅ | ✅ |
| `MODEL_EVALUATE` | ❌ | ✅ | ✅ |
| `MODEL_PROMOTE` | ❌ | ✅ | ✅ |
| `MODEL_PREDICT` | ✅ | ✅ | ✅ |
| `WORKSPACE_DELETE` | ❌ | ❌ | ✅ |

---

## 3. Cryptographic Artifact Integrity Validation

1. **Upload Hashing**: Before storing a model JSON payload, a SHA-256 digest of the raw content is calculated and stored inside the artifact structure.
2. **Read Validation**: When loading an artifact for inference evaluation, `ArtifactStore` re-calculates the SHA-256 digest. If the computed hash does not match, execution fails immediately with `HTTP 400 Bad Request` (`artifact_corrupted`).

---

## 4. Input Sanitization & Path Traversal Prevention

- **Uploaded Filenames**: Stripped of path navigation sequences (`..`, `/`, `\`, null bytes `\x00`).
- **Object Key Prefixing**: Object storage keys are explicitly scoped under `workspaces/{workspace_id}/...`, preventing cross-tenant access.
