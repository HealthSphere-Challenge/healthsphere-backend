# Backend architecture

Status: HS-004 implements the executable application, configuration, error/request middleware, database session, and Alembic foundations. No product routes, services, repositories, models, or tables are implemented. This repository owns application orchestration, not cross-project governance.

Browser → frontend → backend → PostgreSQL. Backend → AI and backend → Agent. The backend is the trusted application entry point; specialized services have no direct browser interface or application database ownership.

## Target stack and planned structure

Python 3.13, FastAPI, Pydantic, synchronous SQLAlchemy 2, psycopg 3, PostgreSQL, Alembic, pytest and httpx. `uv` manages the locked environment. Exact versions are pinned in `pyproject.toml` and `uv.lock`. Deployment topology remains pending HS-016.

Planned modules: `app/api/` routes and dependencies; `app/schemas/` request/response schemas; `app/services/` use cases; `app/repositories/` persistence; `app/models/` SQLAlchemy mappings; `app/integrations/` AI/Agent clients; `app/core/` configuration/security; `app/db/` connection/session lifecycle. Do not create empty architectural layers for their own sake.

Dependency direction: route → service → repository → database. Routes translate HTTP and validation; services enforce use cases, ownership and transaction boundaries; repositories query/persist without HTTP response logic. Pydantic wire schemas are explicit and separate from ORM models; never serialize sensitive columns by accident. Clients isolate transport/auth/timeouts from domain behavior. Tests substitute boundaries rather than spread network calls throughout services.

## Data and product ownership

One user account = one health profile. Backend owns user identity, profile, measurements, assessment history and authorized conversation context. Do not implement delegated/guardian/family permissions. Persist measurements with units and observation time; distinguish unknown from absent and zero. Persist assessment provenance and the input context needed to interpret a historical result, subject to minimization. Conversation retention is 30 days for the prototype; exact tables, deletion operations, and backup behavior remain pending their implementation tickets. HS-002 creates no models or tables.

## Integration behavior

Authenticate and authorize before querying or sending user context. Build minimum AI features from validated profile/measurement data. Validate downstream responses before persistence/return. Retain model identity/version, target/horizon and pipeline provenance. An unavailable or ineligible assessment is not a low score. Agent messages receive only necessary context and approved assessment evidence; Agent cannot alter a predictive result.

Use 2-second connect/10-second total AI timeouts and 2-second connect/30-second total Agent timeouts. Do not retry downstream application requests automatically in Phase 1. Do not hold a database transaction open across remote inference. Conversation retention is 30 days for the prototype and user deletion is required; deletion operations and backup behavior belong to HS-013/016. Map failures into the canonical safe API error while logging request IDs rather than medical payloads.

HS-012 implements assessment orchestration as route → assessment service → feature builder,
AI client and assessment repository. The service reads owned profile/measurement state, ends
that read transaction, invokes AI, then opens a short persistence transaction only for a
validated completed result. The versioned seven-feature input and full AI provenance are
snapshotted with the result so later profile or measurement changes do not alter its meaning.

See [contracts](../api/CONTRACTS.md), [database](../database/DATABASE_STRATEGY.md), [security](../security/SECURITY_AND_PRIVACY.md), and [testing](../testing/TESTING_STRATEGY.md).
