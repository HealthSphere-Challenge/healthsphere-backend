# Cross-service contracts and health metric semantics

Status: approved boundary requirements plus a proposed contract worksheet for HS-002. **No endpoint, JSON schema, authentication transport, or error envelope is finalized or implemented here.** This repository documents its application API and integration responsibilities; AI and Agent retain authority over their own producer semantics and must co-review changes.

## Ownership and interface inventory

| Interface | Producer | Consumer | Responsibility |
|---|---|---|---|
| Frontend ↔ backend | Backend | Frontend | Auth/session, profile, measurement, dashboard, assessment, conversation |
| Backend ↔ AI | AI | Backend | Validated feature input, experimental prediction, explanations and provenance |
| Backend ↔ Agent | Agent | Backend | User turn + minimal authorized context → grounded answer/follow-up/safety state |

Frontend must never bypass backend. The Agent does not call AI to create scores independently; backend supplies any approved assessment context. Only backend reads/writes application PostgreSQL.

## Proposed message requirements to resolve in HS-002

| Area | Input semantics | Output / failure semantics |
|---|---|---|
| Auth | Credential validation; no client-selected ownership | Session/current-user identity; safe invalid/expired/denied errors; transport unresolved |
| Profile | Partial updates, explicit unknown/none, consent-sensitive fields | One authorized profile; distinguish omitted update from explicit clear; exact schema unresolved |
| Measurement | Metric identifier, numeric/structured value, unit, observation time | Persisted measurement, server identity, canonical unit/time; invalid/future/duplicate policy unresolved |
| Dashboard | Authorized current user, temporal query scope | Recent actual metrics with source/time and stale/empty semantics; no fabricated health status |
| Assessment request | Required validated features or authorized backend-selected inputs | Eligible result or explicit insufficient-data/ineligible/unavailable status |
| Assessment result | Producer-approved contract | Target, horizon, population eligibility, score semantics if justified, model/pipeline version, explanation method and limitations |
| Conversation | Turn, conversation reference, minimum permitted context, optional immutable assessment evidence | Answer or follow-up/abstention/urgent status; sources, corpus/prompt/model provenance as applicable; provider-failure semantics |

Exact field names, enums, endpoint paths, JSON types, lengths/limits, status codes, auth headers/cookies and version notation remain unresolved. Proposed schema candidates require linked producer/consumer review and examples before implementation. Do not treat an illustrative `/predict` in Phase 0 as a released API.

## Metric dictionary requirements

For each approved MVP metric, record code/name, datatype, accepted input units, canonical storage unit, conversion/rounding policy, timestamp/timezone rules, collection source, required context, missingness and validation constraints. Blood pressure requires paired systolic/diastolic semantics; weight and height must not be confused with calculated BMI. Candidate metrics in references are not yet an approved clinical range table.

Represent observation time separately from ingestion time. UTC storage with explicit offsets and user-local display is a proposal to finalize, not an inferred implementation. Technical value validation must not silently invent medical normality thresholds. Define staleness, plausible-input bounds and eligibility using justified sources; define clinical labels separately from syntactic validation. Never substitute zero for missing measurements.

## Compatibility, errors and resilience

Record contract version/revision, owners, consumers and change log. Keep producer schemas authoritative and publish/pin machine-readable fixtures/specs during HS-002 and runtime foundations. Consumer generation versus hand-maintained types remains unresolved. A breaking change needs a migration/version strategy and coordinated producer + consumer tests before release; never silently change response shapes.

Errors need stable machine-readable codes, safe human messages, optional field details and correlation metadata. Distinguish validation, unauthenticated, unauthorized, conflict, insufficient input, incompatible model and dependency unavailable. Do not leak stack traces, credentials or user existence unnecessarily. Envelope shape and HTTP mapping await HS-002.

Document service authentication, bounded timeouts, cancellation, retryability, idempotency, payload limits and sync versus asynchronous completion. No automatic retries of unsafe writes. Validate downstream schemas before storing results and preserve actual prediction provenance. Sample contract fixtures must be explicitly synthetic and cannot serve as runtime fallback predictions.

## Change checklist

Identify consumers → document current revision → propose new schema/semantics → update contract tests → update producer → update consumers → verify compatibility and linked CI. HS-002 cannot close with unresolved wire-level decisions required by HS-006 onward; prediction-specific fields also depend on HS-010 target validation.
