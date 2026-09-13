---
name: fastapi-architecture
description: "Plan or implement approved FastAPI route, service, repository and downstream-client changes."
---

# Fastapi Architecture

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Backend Architecture](../../../docs/architecture/BACKEND_ARCHITECTURE.md)

## Workflow

Locate the HTTP boundary, domain use case, persistence boundary and downstream clients affected by the ticket. Keep route validation/translation separate from service business rules and repository queries. Verify ownership before data access and AI context construction. Do not hold DB transactions across slow remote requests. Map client failures into approved API errors without leaking sensitive details. Record unresolved sync/async or architectural package choices rather than inventing them in feature work.
