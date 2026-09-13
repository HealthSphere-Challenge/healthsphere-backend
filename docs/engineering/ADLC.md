# ADLC and engineering delivery — backend

Status: approved Stage 2 governance, 2026-09-13. This repository is independently responsible for its delivery. Cross-repository coordination belongs in approved GitHub Issues/Project; no application repository owns global governance.

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision.

| Mode | Required evidence |
|---|---|
| Discovery | Current behavior, reusable modules, gaps, constraints, unknowns; no coding |
| Brainstorm | User value, alternatives, UX, edge cases, privacy, safety, and test implications; no coding |
| Architecture Check | Affected repos/modules, dependency direction, API/data impact, compatibility, risks; reject boundary violations |
| Plan | Repository, files/modules, steps, acceptance criterion, tests, dependencies, risks for each change |
| Ticket | Approved objective, in/out scope, acceptance criteria, required tests, dependency links |
| Development | Only approved scope; tests added alongside implementation |
| Unit / Integration / Contract | Relevant checks executed; producer and consumer compatibility demonstrated |
| Self Review | Second-reviewer perspective on correctness, complexity, naming, duplication, errors, tests, maintainability |
| QA | Each criterion exercised: happy, invalid, denied, edge, failure, empty and loading paths |
| Security / Healthcare Safety | Auth/ownership, input/privacy/secrets/logs/uploads, grounded claims and urgent behavior where applicable |
| Visual QA | UI comparison against approved references at 1440, 1024, 768, 390 px; hierarchy, states, reflow, keyboard access |
| E2E | Applicable complete user journeys exercised through actual service boundaries |
| PR / CI / Merge decision | Small reviewable diff, evidence, residual risks, passing required checks, explicit authorized merge |

These are working modes, not a requirement to create independent agents. Parallel work is useful only when dependencies and ownership are clear.

## Coding standards

Prefer simple code, small cohesive modules, explicit boundaries, meaningful naming, and dependency inversion only when it adds value. Validate external input, centralize business rules, use structured errors and environment configuration. Do not introduce speculative abstractions or unrelated cleanup. Do not log secrets or medical payloads. Repository-specific standards live in architecture and testing docs.

## Definition of Done

- Acceptance criteria met and approved architecture respected.
- Applicable unit, integration, contract, E2E, accessibility, responsive and visual checks pass.
- Security and healthcare safety reviewed; residual risks documented.
- Configured lint, format, typecheck and build checks pass where relevant.
- Documentation and API/migration compatibility notes updated.
- Required CI passes, review findings resolved, PR merged into main after an authorized merge decision.

Mark nonapplicable gates with a reason; never mark an unavailable or unrun check as passing. Documentation-only Stage 2 work uses link/skill validation, diff review, credential hygiene and raw-asset preservation checks. Runtime tests/builds are unavailable until their approved foundation tickets implement tooling.

## Git and approval boundaries

Use short-lived `feature/`, `fix/`, `test/`, `chore/` or documentation branches and conventional commits (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`, `ci:`, `perf:`). All PRs target main; no develop branch. Never push product work directly to main or merge silently. Record coordinated breaking changes with all consumers before implementation.

The approved foundation is tracked through live issues and review PRs. Product implementation requires the active ticket and plan to be authorized; PR merge requires an explicit authorized decision. Refresh existing GitHub issues before allocating future identifiers. Use linked implementation issues for materially different repository responsibilities, with explicit completion evidence on coordination issues.
