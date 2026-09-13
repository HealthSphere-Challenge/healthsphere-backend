# Proposed GitHub issues — healthsphere-backend

Status: approved issue-body record, delivered to GitHub on 2026-09-13. The table retains stable project IDs; actual GitHub issue numbers are repository-local. Live issue bodies contain actual dependency and coordination links. Refresh GitHub before creating future issues.

Cross-repository coordination will live in approved GitHub Issues/Project. This file contains only issues proposed for this repository, not a project-wide governance authority. Dependency IDs include their repository below; actual issue links are added only after approved creation. Child membership is not a prerequisite cycle: HS-001 children may start after proposal approval; the coordinator closes after their review/merge evidence. HS-016 preparation may overlap QA, but actual deployment waits for HS-015 and hosting approval.

Labels below already exist; no new labels are proposed. Priority P0 applies to all immediate roadmap items; sizes S/M/L are relative, not delivery-date promises. P1/deferred: medical documents, advanced 7/30-day trend screens, recommendations/progress/timeline expansion, Women's Health, guardian/multi-profile accounts and extended preferences. Guardian/multi-profile remains excluded from MVP and requires a future explicit architecture decision.

| ID | Title | Kind | Dependencies | Labels | Size |
|---|---|---|---|---|---|
| [HS-001-BE](#hs-001-be) | Repository foundation: backend | implementation | Stage 2 approval | documentation | M |
| [HS-002](#hs-002) | API Contracts and Health Metric Semantics | implementation | HS-001-BE, HS-001-FE, HS-001-AI, HS-001-AG | documentation | M |
| [HS-004](#hs-004) | Backend + PostgreSQL + Alembic + Testing + CI Foundation | implementation | HS-001-BE | enhancement | M |
| [HS-006](#hs-006) | Authentication and Health Profile Backend | implementation | HS-002, HS-004 | enhancement | L |
| [HS-008](#hs-008) | Health Measurements and Dashboard Backend | implementation | HS-002, HS-006 | enhancement | M |
| [HS-012-BE](#hs-012-be) | Orchestrate and persist risk assessments | implementation | HS-008, HS-011 | enhancement | M |
| [HS-014-BE](#hs-014-be) | Authorized Agent conversation orchestration | implementation | HS-006, HS-013 | enhancement | M |
| [HS-016-BE](#hs-016-be) | Deployment readiness: backend | implementation | HS-012-BE, HS-014-BE | enhancement | M |

# HS-001-BE

Proposed title: **[HS-001-BE] Repository foundation: backend**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `documentation`

## Context

Stage 2 approved the local documentation, skills and support files. Stage 3 created this live issue and authorized the foundation PR; product implementation and PR merge remain outside this stage.

## Objective

Review and deliver the approved Stage 2 foundation in this repository.

## User / Business Value

Keeps approved decisions discoverable and prevents architecture, UX or safety drift.

## Technical Scope

AGENTS, local ADLC, backend architecture, PostgreSQL/migrations, proposed contracts, security/privacy and testing docs; four specialized skills; README and support files.

## Out of Scope

Product runtime/dependencies/endpoints/tables/training/indexing.

## Acceptance Criteria

- [ ] All required repository docs and specialized skills exist with working references.
- [ ] Approved versus proposed/unresolved choices are distinguished; current implementation status is accurate.
- [ ] Existing raw data/design assets preserved byte-for-byte; examples contain no real credentials.
- [ ] Local Stage 2 work is reviewed and merged only through an authorized PR targeting main.

## Testing Requirements

Markdown link audit, skill-creator metadata validation, git diff/whitespace review, ignore/template checks and original-asset checksum preservation.

## Dependencies

- Created under the explicit Stage 3 issue-delivery approval; product implementation still requires a later execution authorization.
- Coordination membership: [HS-001](https://github.com/HealthSphere-Challenge/healthsphere-frontend/issues/2); not a blocking dependency on coordinator closure.

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-002

Proposed title: **[HS-002] API Contracts and Health Metric Semantics**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `documentation`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Finalize version-conscious application and specialized-service contracts with all producers/consumers.

## User / Business Value

Teams can integrate without incompatible payloads or misleading health meanings.

## Technical Scope

Resolve auth transport with HS-006 planning; define endpoints, schemas/examples, metric dictionary, units/time/missingness, safe errors, service auth, limits/timeouts/idempotency; record contract ownership and compatibility policy. Prediction-specific fields require HS-010 target-gate evidence; base contracts can be released earlier.

## Out of Scope

Implementing auth/product endpoints, training, arbitrary clinical ranges.

## Acceptance Criteria

- [ ] All three interfaces have producer/consumer-reviewed schemas and valid synthetic fixtures.
- [ ] Metric semantics distinguish unknown/none/zero and separate validation from medical interpretation.
- [ ] AI provenance/eligibility and Agent safety/source states are explicit.
- [ ] Breaking-change process and version/fixture ownership are documented; no unresolved field required by dependent implementation is hidden.

## Testing Requirements

Validate fixture/schema positive and negative cases; review consumer compatibility, error mapping and units; executable contract integration follows each runtime foundation.

## Dependencies

- `HS-001-BE` — healthsphere-backend
- `HS-001-FE` — healthsphere-frontend
- `HS-001-AI` — healthsphere-ai
- `HS-001-AG` — healthsphere-agent

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-004

Proposed title: **[HS-004] Backend + PostgreSQL + Alembic + Testing + CI Foundation**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Provide FastAPI and isolated PostgreSQL migration/test infrastructure.

## User / Business Value

Enables reliable application persistence without ad-hoc schema changes.

## Technical Scope

Choose dependency tool/versions and sync/async execution; config/session lifecycle, psycopg 3, SQLAlchemy 2, Alembic environment, pytest/httpx, lint/format and PostgreSQL CI; non-product health/readiness behavior if needed.

## Out of Scope

Users/profiles/measurement tables, authentication and product APIs.

## Acceptance Criteria

- [ ] Fresh setup and test DB provisioning documented and verified.
- [ ] TEST_DATABASE_URL cannot silently use the development database.
- [ ] Alembic history and fresh-upgrade checks work without product tables.
- [ ] Configured CI passes with safe env examples and no secret logs.

## Testing Requirements

Config failure and DB-identity guard tests, PostgreSQL connection/session lifecycle, migration setup validation, smoke endpoint if added, lint/format/pytest CI.

## Dependencies

- `HS-001-BE` — healthsphere-backend

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-006

Proposed title: **[HS-006] Authentication and Health Profile Backend**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: L · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Implement authenticated access and one owned progressive health profile.

## User / Business Value

Users can securely retain the context needed for health tracking.

## Technical Scope

Record auth/session/CSRF/expiry/logout design; register/login/current-user/logout; validated partial profile persistence and ownership; SQLAlchemy models/Alembic migrations; basic profile review/update; minimum-age/sensitive-field policy decision.

## Out of Scope

Guardian/family accounts, Google OAuth, password recovery unless separately approved.

## Acceptance Criteria

- [ ] One user account has one profile enforced by constraints and services.
- [ ] Auth/session and denial paths behave according to approved contracts.
- [ ] Profile supports partial progress and explicit unknown/none semantics without data leakage.
- [ ] Cross-user reads/updates fail; migrations and safe logging verified.

## Testing Requirements

pytest service tests, PostgreSQL register/login/profile integration, schema/migration tests, cross-user and invalid-session cases, auth-contract checks.

## Dependencies

- `HS-002` — healthsphere-backend
- `HS-004` — healthsphere-backend

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-008

Proposed title: **[HS-008] Health Measurements and Dashboard Backend**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Persist owned measurements and provide an honest dashboard summary.

## User / Business Value

Users can retain and review their actual health indicators.

## Technical Scope

Approved metric schemas, unit/time validation, SQLAlchemy/Alembic, create/list/latest and basic dashboard data; ownership, duplicate-write policy and missing/stale semantics.

## Out of Scope

Advanced 7/30-day screens, document processing, clinical threshold invention.

## Acceptance Criteria

- [ ] Measurements retain canonical units, observation time and owner.
- [ ] Dashboard displays actual latest data or explicit absence/staleness.
- [ ] Invalid units/times and cross-user operations are rejected.
- [ ] No fabricated normality labels or risk scores.

## Testing Requirements

Unit conversion/validation tests, PostgreSQL persistence/ownership/ordering integration, migrations, consumer fixtures and error contracts.

## Dependencies

- `HS-002` — healthsphere-backend
- `HS-006` — healthsphere-backend

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-012-BE

Proposed title: **[HS-012-BE] Orchestrate and persist risk assessments**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Integrate owned application data with the AI inference service.

## User / Business Value

Assessment history remains traceable and protected.

## Technical Scope

AI client, validated feature construction, eligibility, bounded transport errors, authorized assessment persistence/retrieval and provenance/input snapshot; migrations/contract mapping.

## Out of Scope

Frontend UI, model training, Agent-generated scores.

## Acceptance Criteria

- [ ] Authorization precedes AI calls and minimum required input is sent.
- [ ] Actual result and provenance persist with the approved historical input semantics.
- [ ] Timeout/invalid model/insufficient-data paths return explicit errors/status without invented risk.

## Testing Requirements

Service/client unit tests, PostgreSQL assessment/ownership/migration integration, AI consumer/frontend producer contracts, timeout/error and no-sensitive-log cases.

## Dependencies

- `HS-008` — healthsphere-backend
- `HS-011` — healthsphere-ai

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-014-BE

Proposed title: **[HS-014-BE] Authorized Agent conversation orchestration**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Control conversation ownership and minimum-context access to Agent.

## User / Business Value

Conversation content stays scoped to the correct user and preserves safety states.

## Technical Scope

Agent client, request validation, conversation state/retention decision, authorized context selection, response/source/safety mapping, bounded errors and persistence/migrations if selected. Optional assessment explanation depends additionally on HS-012-BE.

## Out of Scope

Agent generation/retrieval code, document uploads, guardian access.

## Acceptance Criteria

- [ ] One user cannot read/write another conversation.
- [ ] Only necessary context reaches Agent; source and urgent/abstention states remain intact.
- [ ] Provider outage/retries/cancellation do not create duplicate or fabricated responses.

## Testing Requirements

Service unit, PostgreSQL ownership/state integration as applicable, Agent consumer/frontend producer contracts, timeout/context-minimization and safe-log tests.

## Dependencies

- `HS-006` — healthsphere-backend
- `HS-013` — healthsphere-agent

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-016-BE

Proposed title: **[HS-016-BE] Deployment readiness: backend**

Repository: `HealthSphere-Challenge/healthsphere-backend` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Prepare this service for the approved integrated prototype release.

## User / Business Value

The service can be deployed and recovered consistently within its existing boundary.

## Technical Scope

Backend deployment configuration, approved PostgreSQL connection/provisioning/migration plan, CORS/session/service-auth integration, health/readiness, synthetic demo setup and rollback notes. Configuration preparation can precede HS-015; actual publication requires passing HS-015 and an explicitly approved hosting/deployment plan.

## Out of Scope

Unapproved publication/spend, new service boundaries or product features.

## Acceptance Criteria

- [ ] Application DB and internal client configuration work with ownership/session controls; no secrets/logged medical payloads.
- [ ] Document verified run/configuration/health/rollback steps with release revisions.
- [ ] Use synthetic demo data and an approved secrets mechanism; no production claims.

## Testing Requirements

Migration/release smoke, authenticated/denied calls, internal dependency failures, secret/config review and rollback compatibility.

## Dependencies

- `HS-012-BE` — healthsphere-backend
- `HS-014-BE` — healthsphere-backend
- HS-015 (frontend) and approved hosting/publication plan gate actual deployment; configuration preparation may proceed earlier.

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.
