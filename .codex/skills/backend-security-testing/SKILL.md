---
name: backend-security-testing
description: "Verify HealthSphere authorization, privacy and failure behavior for approved backend changes."
---

# Backend Security Testing

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Security And Privacy](../../../docs/security/SECURITY_AND_PRIVACY.md)
- [Testing Strategy](../../../docs/testing/TESTING_STRATEGY.md)

## Workflow

Map the affected trust boundary and acceptance criteria to tests. Exercise unauthenticated, expired-session, cross-user, invalid-input and downstream-failure paths. Inspect logs/errors/configuration for medical payloads or credentials. Verify only minimum context reaches AI/Agent and ownership cannot be client-selected. Cover CSRF/revocation according to the approved auth design; do not assume a transport. For an approved upload feature, test type/size/storage access and processing failures. Record actual checks and untested risks.
