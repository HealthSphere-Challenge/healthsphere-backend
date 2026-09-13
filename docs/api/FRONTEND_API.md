# Frontend-facing API contract

Status: **APPROVED CONTRACT for HS-002; documentation only.** This is the browser-facing subset of [the authoritative Phase 1 contract](CONTRACTS.md). Authentication behavior is **PENDING HS-006**, measurement behavior **PENDING HS-008**, assessment semantics **PENDING HS-010**, and conversation behavior **PENDING HS-013**.

## Boundary

The frontend calls only the backend under `/api/v1`. It never calls AI, Agent, PostgreSQL, or an LLM provider. Requests and responses use JSON except responses with no body. The preferred deployment is same-site. Approved cross-origin deployment must use explicit origins and credentials.

## Endpoint inventory

| Method | Path | Request | Success |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | credentials + CSRF as applicable | `201` user/profile resource |
| `POST` | `/api/v1/auth/login` | credentials + CSRF as applicable | `200` user/profile resource + session cookie |
| `POST` | `/api/v1/auth/logout` | CSRF header | `204` |
| `GET` | `/api/v1/me` | session cookie | `200` user/profile resource |
| `PATCH` | `/api/v1/profile` | partial profile fields + CSRF | `200` user/profile resource |
| `POST` | `/api/v1/measurements` | typed measurement + CSRF | `201` measurement resource |
| `GET` | `/api/v1/measurements?cursor=` | optional opaque cursor | `200` paginated measurements |
| `GET` | `/api/v1/dashboard` | session cookie | `200` dashboard resource |
| `POST` | `/api/v1/assessments` | CSRF header | `202` or `200` assessment resource; exact completion choice **PENDING HS-012-BE** |
| `GET` | `/api/v1/assessments/{assessment_id}` | session cookie | `200` assessment resource |
| `GET` | `/api/v1/assessments?cursor=` | optional opaque cursor | `200` paginated assessments |
| `POST` | `/api/v1/conversations` | optional approved creation fields + CSRF | `201` conversation resource |
| `GET` | `/api/v1/conversations?cursor=` | optional opaque cursor | `200` paginated conversation summaries |
| `GET` | `/api/v1/conversations/{conversation_id}` | session cookie | `200` conversation resource |
| `DELETE` | `/api/v1/conversations/{conversation_id}` | CSRF header | `204` |
| `POST` | `/api/v1/conversations/{conversation_id}/messages` | `{ "content": string }` + CSRF | `201` assistant message resource |

Exact credential fields, limits, and assessment sync/async completion are owned by the cited implementation tickets. They must retain the resource/error shapes in the authoritative contract.

## Consumer rules

- Send the session cookie with credentialed requests; JavaScript cannot read the HttpOnly cookie.
- Send the session-bound `X-CSRF-Token` on state-changing requests after the HS-006 bootstrap flow supplies it.
- Treat `401` as an authentication-state transition and clear user-scoped caches.
- Render `403`, validation, dependency, unavailable, insufficient-data, ineligible, abstention, and urgent states explicitly.
- Never interpret `null` measurement/assessment data as zero, healthy, or low risk.
- Do not parse cursors or derive BMI locally as authoritative data.
- Validate response bodies at the boundary with Zod before putting them into TanStack Query state.
- Use `X-Request-ID` in support/error correlation without displaying sensitive payloads.

## Partial profile update example

```json
{
  "sex_at_birth": null,
  "medical_conditions": [],
  "allergies": ["peanut"]
}
```

Here `sex_at_birth` is explicitly cleared, `medical_conditions` explicitly records none, `allergies` records one structured value, and all omitted fields remain unchanged.

## Contract testing

Backend Pydantic/OpenAPI is the producer. Frontend strict TypeScript and Zod schemas are the consumer. HS-003/feature tickets will add synthetic response fixtures validated by backend producer tests and frontend consumer tests. TypeScript OpenAPI client generation is deferred until the contract and generation workflow are proven.
