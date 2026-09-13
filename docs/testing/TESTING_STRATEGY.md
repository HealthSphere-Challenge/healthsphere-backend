# Backend testing strategy

Status: planned for HS-004; no executable application, tests or CI yet.

- Unit: pytest for services, validation, ownership decisions and downstream response/error mapping. Mock repositories/clients at explicit boundaries; avoid HTTP-only unit tests that miss domain rules.
- Integration: FastAPI/httpx against isolated PostgreSQL using `TEST_DATABASE_URL`; register/login, progressive profile, measurement and assessment persistence, authorized conversation access, cross-user denials and rollback behavior as features arrive.
- Migration: clean database upgrade, single intended head, previous-schema upgrade and supported rollback/compatibility validation. Review migrations and fail closed on unsafe DB identity.
- Contract: backend Pydantic/OpenAPI is the frontend-facing producer; backend is consumer of AI and Agent Pydantic contracts. Future feature tickets add synthetic fixtures checked by each producer and consumer without a fifth contract repository. Cover canonical units, UUIDv4, RFC 3339 offsets/UTC normalization, omitted/null/empty behavior, invalid versions, unavailable/ineligible results, provenance, and Agent abstention/urgent states. A TypeScript OpenAPI client is not generated yet.
- Security: authentication/authorization, invalid input, safe errors/logging, session expiry/revocation, CSRF where relevant, secrets/dependencies. Upload checks remain deferred with the feature.
- Integrated E2E: support frontend-owned Playwright journeys with isolated synthetic data and actual downstream service contracts. Backend tests alone do not establish UI accessibility or live ML behavior.

CI minimum: reproducible `uv` dependency install on Python 3.13, lint/format validation, pytest and PostgreSQL migration/integration jobs. Exact package, lint tool, workflow versions and commands are HS-004 decisions; do not invent passing results. Avoid mandatory external paid LLM calls in routine deterministic CI.

Each ticket records acceptance evidence and residual risks. Stage 2 verifies docs/skills/support-file hygiene only; HS-015 coordinates later release-level QA without replacing each repository's tests.
