---
name: postgresql-sqlalchemy
description: "Handle approved HealthSphere persistence and Alembic migration changes with PostgreSQL validation."
---

# Postgresql Sqlalchemy

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Database Strategy](../../../docs/database/DATABASE_STRATEGY.md)

## Workflow

Review the model, wire-schema, repository/service and migration impact together. Verify test DB identity is isolated before migration or cleanup; fail if TEST_DATABASE_URL is missing or identifies development storage. Review generated migration SQL for drops, defaults/backfills and compatibility. Validate clean and previous-schema upgrade plus supported rollback. Preserve a single intended head and document irreversible changes. Never substitute permanent create_all or manual table edits for Alembic.
