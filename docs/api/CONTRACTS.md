# Phase 1 API contracts

Status: **APPROVED CONTRACT for HS-002; documentation only.** No endpoint, schema, session, database model, or downstream service is implemented by this document. Prediction semantics marked **PENDING HS-010**, authentication implementation marked **PENDING HS-006**, and Agent behavior marked **PENDING HS-013** are not released behavior.

Contract revision: `phase1-hs002-2026-09-13`

## Ownership and compatibility

| Interface | Producer | Consumer | Authoritative contract |
|---|---|---|---|
| Browser ↔ backend | Backend | Frontend | This document and [frontend API](FRONTEND_API.md) |
| Backend → AI → backend | AI | Backend | This document plus the AI repository inference contract |
| Backend → Agent → backend | Agent | Backend | This document plus the Agent repository contract |

The browser calls the backend only. The backend alone owns application authorization and PostgreSQL persistence. AI and Agent services have no browser-facing application API and no application-database access. A breaking change requires coordinated producer and consumer review, updated examples/fixtures, and an explicit version or migration strategy.

## Common wire rules — APPROVED CONTRACT

- External paths begin with `/api/v1`; service-only paths begin with `/internal/v1`.
- JSON property names use `snake_case`.
- Application identifiers are UUIDv4 strings. PostgreSQL stores them as `uuid`.
- API timestamps use RFC 3339 UTC with milliseconds, for example `2026-09-13T09:05:43.000Z`. Submitted observation timestamps must include `Z` or an explicit numeric offset. PostgreSQL stores instants as `timestamptz` normalized to UTC.
- Calendar dates use `YYYY-MM-DD` and have no timezone, for example `1990-06-15`.
- Responses return the typed resource directly. Lists use `{ "items": [...], "next_cursor": string | null }`.
- Opaque cursors are supplied with `?cursor=`. Consumers must not parse or construct them. Default and maximum page sizes are **PENDING implementation ticket**; clients must accept fewer items than requested.
- A client may send `X-Request-ID` using a UUIDv4. The backend validates or replaces it, returns the effective value in `X-Request-ID`, and forwards it to downstream services. Services generate one when absent. Request IDs are correlation metadata, never authentication.
- Example values are synthetic contract fixtures, not runtime fallbacks or clinical guidance.

### Omitted, null, and empty

- In a partial-update request, an omitted property means “leave unchanged.”
- Explicit `null` means “clear this optional value” only when the field schema permits null.
- Empty arrays mean “the user reports none.” `null` means “unknown/not provided.”
- Response fields documented as required remain present even when their value is `null`.
- Missing observations never become zero. Unavailable or ineligible assessments never become a low score. Agent abstention or urgency never becomes an ordinary answer.

## Authentication — APPROVED CONTRACT, PENDING HS-006

HS-006 will implement opaque server-side sessions. The browser receives a `Secure`, `HttpOnly`, `SameSite=Lax` cookie. The server stores only a cryptographic hash of the session identifier. The absolute session lifetime is 7 days, idle timeout is 24 hours, and concurrent sessions are allowed. State-changing requests require session-bound CSRF protection through the `X-CSRF-Token` header. The token-delivery/bootstrap mechanism and exact cookie name are **PENDING HS-006**.

Prefer same-site frontend/backend routing. Any cross-origin deployment requires an explicit trusted-origin allowlist and credentialed CORS; wildcard `*` is forbidden with credentials. Internal AI and Agent requests use service-specific opaque bearer credentials, held only by the backend and downstream services; exact provisioning and rotation are **PENDING HS-016**.

## Canonical errors — APPROVED CONTRACT

All non-2xx external and internal responses use:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be validated.",
    "details": [
      {
        "path": "body.measured_at",
        "code": "invalid_timestamp",
        "message": "Provide an RFC 3339 timestamp with an explicit offset."
      }
    ],
    "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
    "retry_after_seconds": null
  }
}
```

`details` is an array or `null`; `retry_after_seconds` is an integer or `null`. Safe messages never expose stack traces, credentials, user-existence checks, medical payloads, or downstream provider bodies.

| HTTP | Stable code | Meaning |
|---:|---|---|
| 400 | `invalid_request` | Request is structurally valid but semantically invalid |
| 401 | `authentication_required` | Session or service credential is missing/invalid/expired |
| 403 | `access_denied` or `csrf_failed` | Identity lacks access or CSRF validation failed |
| 404 | `resource_not_found` | Authorized resource is absent; do not disclose another user's resource |
| 409 | `conflict` | Current state conflicts with the request |
| 422 | `validation_error`, `insufficient_data`, or `ineligible` | Field validation or explicit assessment eligibility failure |
| 429 | `rate_limited` | Limit reached; retry metadata may be supplied |
| 502 | `downstream_invalid_response` | A downstream response failed schema validation |
| 503 | `dependency_unavailable` | Required service is unavailable |
| 504 | `dependency_timeout` | Required service exceeded its deadline |
| 500 | `internal_error` | Safe unexpected failure |

## User and profile — APPROVED CONTRACT, PENDING HS-006

One user has exactly one health profile. Minimum account age is 18. Users under 18 are unsupported in the Phase 1 MVP. `sex_at_birth` is optional, sensitive, and never inferred from name or other data.

```json
{
  "user": {
    "id": "157318f6-13b7-42fd-a390-e7691f396a71",
    "email": "alex@example.test",
    "created_at": "2026-09-13T09:05:43.000Z"
  },
  "profile": {
    "id": "c30d6195-0aea-4825-a12a-4a56de46cb56",
    "date_of_birth": "1990-06-15",
    "sex_at_birth": "prefer_not_to_say",
    "height_cm": 172.5,
    "medical_conditions": ["hypertension"],
    "medications": [],
    "allergies": null,
    "age_years": 36,
    "latest_weight": {
      "value": 74.2,
      "unit": "kg",
      "measured_at": "2026-09-12T07:30:00.000Z"
    },
    "bmi": {
      "value": 24.95,
      "unit": "kg/m2",
      "derived_from_measurement_id": "723638db-84d1-43bf-8616-06c0e9d57f7f"
    },
    "updated_at": "2026-09-13T09:05:43.000Z"
  }
}
```

`date_of_birth`, `sex_at_birth`, and `height_cm` may be null until provided. `sex_at_birth` values are `female`, `male`, `intersex`, or `prefer_not_to_say`. The structured vocabularies for medical conditions, medications, and allergies are **PENDING HS-006**; unrestricted free-text medical history is excluded unless a later approved use case requires it. `latest_weight` and `bmi` are read-only projections and may be null. Age is calculated at request time; BMI is derived from the latest authoritative weight measurement and profile height.

## Health measurement — APPROVED CONTRACT

See the complete dictionary and validation rules in [health metrics](HEALTH_METRICS.md).

```json
{
  "id": "723638db-84d1-43bf-8616-06c0e9d57f7f",
  "metric": "blood_pressure",
  "value": { "systolic": 118, "diastolic": 76 },
  "unit": "mmHg",
  "context": null,
  "measured_at": "2026-09-12T07:30:00.000Z",
  "recorded_at": "2026-09-12T07:31:12.000Z",
  "source": "manual",
  "note": null
}
```

The request omits server-generated `id` and `recorded_at`. `note` is optional, may be null, and is limited to 1,000 characters. `source` is `manual` for Phase 1 input. BMI is returned only as a derived projection, rounded to two decimal places, and is rejected as measurement input.

## Dashboard — APPROVED CONTRACT

`GET /api/v1/dashboard` returns actual authorized data. Empty and stale states are data, not fabricated health status.

```json
{
  "generated_at": "2026-09-13T09:05:43.000Z",
  "latest_measurements": {
    "heart_rate": null,
    "blood_pressure": {
      "id": "723638db-84d1-43bf-8616-06c0e9d57f7f",
      "metric": "blood_pressure",
      "value": { "systolic": 118, "diastolic": 76 },
      "unit": "mmHg",
      "context": null,
      "measured_at": "2026-09-12T07:30:00.000Z",
      "recorded_at": "2026-09-12T07:31:12.000Z",
      "source": "manual",
      "note": null
    }
  },
  "latest_assessment": null
}
```

The map contains each approved metric key; a value is null when no observation/projection exists. Freshness labels or clinical interpretations are not defined in HS-002.

## Assessment — transport approved; semantics PENDING HS-010

`POST /api/v1/assessments` asks the backend to assemble authorized inputs and invoke AI. The browser cannot submit a score or model features. `GET /api/v1/assessments/{assessment_id}` returns a stored result; `GET /api/v1/assessments?cursor=` returns a paginated history.

```json
{
  "id": "c63f9048-9510-4eb5-8c0d-73bb5cb3fe8b",
  "status": "insufficient_data",
  "result": null,
  "reason": { "code": "minimum_inputs_missing", "missing_fields": ["pending_hs_010"] },
  "created_at": "2026-09-13T09:05:43.000Z"
}
```

Statuses are `completed`, `insufficient_data`, `ineligible`, or `unavailable`. A completed `result` must carry the approved target, eligible population, horizon, score semantics, calibration/version provenance, labels/thresholds if any, and explanation method. Every one of those concepts remains **PENDING HS-010**. Until HS-010 approves them, no completed-result example or fallback score is valid.

## Conversation — transport approved; behavior PENDING HS-013

`POST /api/v1/conversations` creates a conversation. `GET /api/v1/conversations?cursor=` lists the current user's retained conversations. `GET /api/v1/conversations/{conversation_id}` returns one conversation. `DELETE /api/v1/conversations/{conversation_id}` deletes it. `POST /api/v1/conversations/{conversation_id}/messages` sends a user turn through the backend to Agent.

```json
{
  "id": "e8904ea9-8873-48bb-a344-c212914d9893",
  "created_at": "2026-09-13T09:05:43.000Z",
  "updated_at": "2026-09-13T09:06:08.000Z",
  "expires_at": "2026-10-13T09:05:43.000Z",
  "messages": [
    {
      "id": "f59e8db7-7453-47ea-a5a1-a00cc966e742",
      "role": "user",
      "content": "What can affect sleep duration?",
      "created_at": "2026-09-13T09:06:00.000Z"
    },
    {
      "id": "a9ee0383-7f46-49de-b5b8-0c89ba323714",
      "role": "assistant",
      "content": "Several habits and health factors can affect sleep duration.",
      "response_type": "answer",
      "sources": [],
      "safety": { "urgent": false, "reason": null },
      "uncertainty": "General information only; this does not determine the cause for an individual.",
      "created_at": "2026-09-13T09:06:08.000Z"
    }
  ]
}
```

Conversation retention is 30 days for the prototype, measured from creation for this contract. Users must be able to delete conversations. Operational deletion timing and backup behavior are **PENDING HS-013/HS-016**. The exact title behavior, message limits, source shape, safety taxonomy, and approved user-facing copy are **PENDING HS-013**. Assistant response types are `answer`, `follow_up`, `abstention`, or `urgent`; consumers preserve these distinct states.

## Backend → AI → backend — transport approved; semantics PENDING HS-010

The backend calls `POST /internal/v1/inferences` with an opaque bearer credential, `X-Request-ID`, and a schema-versioned body. The AI connect timeout is 2 seconds and total timeout is 10 seconds. There are no automatic application retries initially.

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "subject_ref": "f630d635-64e2-432b-8175-60f61d220d4d",
  "features": { "pending_hs_010": true }
}
```

The pseudonymous `subject_ref` is request-scoped or service-scoped and is not the application user ID. AI must return one of `completed`, `insufficient_data`, `ineligible`, or `unavailable`. A completed payload is forbidden until HS-010 defines the target, eligible population, horizon, feature schema, minimum inputs, score semantics, calibration, risk labels, thresholds, and explanation method. See the AI repository contract for the stable provenance/error structure.

## Backend → Agent → backend — transport approved; behavior PENDING HS-013

The backend calls `POST /internal/v1/agent/responses` with an opaque bearer credential, `X-Request-ID`, the current user turn, bounded recent turns, and only necessary authorized profile/measurement/assessment context. The Agent connect timeout is 2 seconds and total timeout is 30 seconds. There are no automatic application retries initially.

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "conversation_ref": "7a19544c-e55f-4ea8-96b9-557575027fb4",
  "user_message": "What can affect sleep duration?",
  "recent_turns": [],
  "health_context": {
    "profile": null,
    "measurements": [],
    "assessment": null
  }
}
```

The Agent returns a response type, grounded content when available, sources, safety state, uncertainty, and provenance. It cannot generate or alter a predictive score. Exact context caps and response/safety schemas are **PENDING HS-013** and documented in the Agent repository contract.

## Contract-test ownership

- Backend owns Pydantic schemas and OpenAPI for the external API and validates both downstream responses.
- Frontend owns strict TypeScript types plus Zod runtime consumer schemas.
- AI owns Pydantic producer/consumer schemas for inference.
- Agent owns Pydantic producer/consumer schemas for Agent exchange.
- A fifth shared-contract repository is forbidden. A generated TypeScript OpenAPI client is deferred.
- Future tickets will commit synthetic fixture examples beside each consumer and verify them against producer schemas in CI. HS-002 documents this workflow but adds no runtime tests or dependencies.

## Revision policy

Compatible additions must remain optional for existing consumers. Removing/renaming fields, changing types, units, enum meaning, nullability, or endpoint behavior is breaking and requires a new API/schema version plus coordinated rollout. Producer PRs link consumer PRs and record fixtures, CI evidence, deployment order, and rollback considerations.
