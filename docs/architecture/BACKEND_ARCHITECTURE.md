# Backend architecture

Status: approved direction, no application implementation. This repository owns application orchestration, not cross-project governance. Each repository maintains its own instructions and detailed architecture; GitHub Issues/Project coordinates delivery.

Browser → frontend → backend → PostgreSQL. Backend → AI and backend → Agent. The backend is the trusted application entry point; specialized services have no direct browser interface or application database ownership.

## Target stack and planned structure

Python, FastAPI, Pydantic, SQLAlchemy 2, psycopg 3, PostgreSQL, Alembic, pytest and httpx. Versions, dependency/lock tool, synchronous versus asynchronous database execution and deployment topology are unresolved for HS-004.

Planned modules: `app/api/` routes and dependencies; `app/schemas/` request/response schemas; `app/services/` use cases; `app/repositories/` persistence; `app/models/` SQLAlchemy mappings; `app/integrations/` AI/Agent clients; `app/core/` configuration/security; `app/db/` connection/session lifecycle. Do not create empty architectural layers for their own sake.

Dependency direction: route → service → repository → database. Routes translate HTTP and validation; services enforce use cases, ownership and transaction boundaries; repositories query/persist without HTTP response logic. Pydantic wire schemas are explicit and separate from ORM models; never serialize sensitive columns by accident. Clients isolate transport/auth/timeouts from domain behavior. Tests substitute boundaries rather than spread network calls throughout services.

## Data and product ownership

One user account = one health profile. Backend owns user identity, profile, measurements, assessment history and authorized conversation context. Do not implement delegated/guardian/family permissions. Persist measurements with units and observation time; distinguish unknown from absent and zero. Persist assessment provenance and the input context needed to interpret a historical result, subject to minimization. Exact tables and retention rules remain unresolved until their tickets; Stage 2 creates no models or tables.

## Integration behavior

Authenticate and authorize before querying or sending user context. Build minimum AI features from validated profile/measurement data. Validate downstream responses before persistence/return. Retain model identity/version, target/horizon and pipeline provenance. An unavailable or ineligible assessment is not a low score. Agent messages receive only necessary context and approved assessment evidence; Agent cannot alter a predictive result.

Set bounded request timeouts; avoid retries of non-idempotent operations without an idempotency design. Do not hold a database transaction open across slow remote inference. Exact retry budgets, idempotency keys, sync/async response mode and conversation retention are HS-002 decisions. Map failures into stable safe API errors, logging correlation metadata rather than medical payloads.

See [contracts](../api/CONTRACTS.md), [database](../database/DATABASE_STRATEGY.md), [security](../security/SECURITY_AND_PRIVACY.md), and [testing](../testing/TESTING_STRATEGY.md).
