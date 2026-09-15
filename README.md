# HealthSphere — FastAPI application orchestrator

## Foundation status

The HS-004 executable foundation provides FastAPI composition, strict settings, safe errors/request correlation, synchronous SQLAlchemy/PostgreSQL sessions, Alembic metadata wiring, tests, and pull-request CI. It contains no product endpoints or product tables.

Exactly four independent repositories: browser → frontend → backend → PostgreSQL; backend → AI and backend → Agent. Frontend never calls specialized services directly. Backend owns application data/access, while each repository owns its own architecture/governance. Cross-repository delivery belongs in GitHub Issues/Project after approval.

One account = one health profile; English MVP. Guardian/family/multi-profile access is excluded. ML is experimental and cannot claim clinical validity. Agent never creates predictive scores. See [AGENTS.md](AGENTS.md) before work.

## Documentation

- [Contracts](docs/api/CONTRACTS.md)
- [Backend Architecture](docs/architecture/BACKEND_ARCHITECTURE.md)
- [Database Strategy](docs/database/DATABASE_STRATEGY.md)
- [Adlc](docs/engineering/ADLC.md)
- [Security And Privacy](docs/security/SECURITY_AND_PRIVACY.md)
- [Testing Strategy](docs/testing/TESTING_STRATEGY.md)
- [Proposed GitHub issues](docs/planning/PROPOSED_ISSUES.md)

## Local configuration and delivery

Requires Python 3.13 and `uv`. Copy `.env.example` to `.env`, replace `CHANGE_ME`, and provision separate development and test PostgreSQL databases. `.env` is ignored and must never be committed.

```bash
uv sync --locked --dev
uv run uvicorn app.main:create_app --factory --reload
```

Run foundation checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit
TEST_DATABASE_URL=postgresql+psycopg://healthsphere_test:CHANGE_ME@localhost:5432/healthsphere_test uv run pytest tests/integration
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic check
```

Create future approved schema migrations with `uv run alembic revision --autogenerate -m "description"`. Apply with `uv run alembic upgrade head`; revert one revision with `uv run alembic downgrade -1`. HS-004 intentionally has no baseline product migration because metadata is empty.

Use short-lived branches → PR → main, no develop; no silent merge.
# HS-012 hypertension assessments

The browser calls the authenticated backend assessment API; it never calls
`healthsphere-ai` directly. Configure the internal service connection:

```bash
HEALTHSPHERE_AI_SERVICE_URL=http://127.0.0.1:8001
HEALTHSPHERE_AI_INTERNAL_TOKEN=replace-with-the-shared-local-secret
HEALTHSPHERE_AI_CONNECT_TIMEOUT_SECONDS=2
HEALTHSPHERE_AI_TIMEOUT_SECONDS=10
```

The backend exposes synchronous `POST /api/v1/assessments`,
`GET /api/v1/assessments`, and `GET /api/v1/assessments/{assessment_id}`.
Creation requires the existing session cookie and CSRF header. It builds
`hypertension_features_v1` from profile data and the latest authoritative paired BP,
heart-rate and weight records, then calls `POST /internal/v1/inferences` with bearer
authentication and matching request IDs.

Only completed results are persisted. The record preserves the seven-value input snapshot,
target/schema/model/preprocessing versions, horizon, score semantics, calibration flag and
correlation ID. Other outcomes contain no score. The score is an uncalibrated experimental
estimate produced by a model trained only on synthetic Synthea data; it is not clinically
validated and must not be used for diagnosis, treatment, emergency triage or a risk category.

For a manual smoke test, start PostgreSQL and apply `alembic upgrade head`; start the AI
service on port 8001 with the same internal token; start this backend; register/login; add a
date of birth, height, paired BP, optional heart rate and weight; then POST an assessment and
retrieve it from the assessment history. No automatic AI retry is performed.

## HS-014 assistant orchestration

The authenticated conversation API is exposed only by this backend at
`/api/v1/conversations`. Configure its private agent connection with
`HEALTHSPHERE_AGENT_SERVICE_URL` and `HEALTHSPHERE_AGENT_INTERNAL_TOKEN`; the token is never
sent to the browser. The backend sends at most six recent turns, no profile or measurement
history, and includes an assessment only when the browser supplies its ID and the record
belongs to the current user.

Conversations expire after 30 days and can be deleted through the API. A message exchange
is stored only after the agent returns a valid, correlated response, so an unavailable or
incompatible agent leaves no unmatched user message. The backend performs no automatic
retry and preserves the response state, sources, safety, uncertainty, and provenance.

Assistant context is routed before Agent invocation. Explicit questions about the signed-in
user's profile or latest saved measurement are answered deterministically from ownership-
scoped backend records with no MedQuAD sources. General medical questions still use Agent
RAG, selected assessments still send only their approved context, and broad personal-data
requests ask the user to narrow the request. These application-data answers follow the same
30-day conversation retention policy and are never written to logs.
