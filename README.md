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
