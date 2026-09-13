# Security and privacy architecture

Status: approved Phase 1 requirements; implementation remains **PENDING HS-006** and provider/deployment controls remain **PENDING HS-016**. This is product engineering guidance, not a claim of regulatory compliance.

## Trust and access

Backend authenticates requests and enforces ownership for every profile, measurement, assessment and conversation operation. One account = one profile; no guardian, delegated or multi-profile access. Client route guards are UX only. Never trust a client-provided user ID as authorization. Verify cross-user denial and missing/expired credentials in integration tests.

HS-006 implements opaque server-side sessions. The browser cookie is `Secure`, `HttpOnly`, and `SameSite=Lax`; the server stores only a cryptographic hash of its identifier. Sessions have a 7-day absolute lifetime, a 24-hour idle timeout, and may be concurrent. Logout/revocation and session-bound CSRF protection apply to state-changing requests; exact cookie name, CSRF bootstrap/delivery, password hashing settings, and rate limits are **PENDING HS-006**. Google OAuth and password recovery are separate unapproved capabilities.

Prefer same-site frontend/backend routing. If an approved environment is cross-origin, CORS uses an explicit trusted-origin allowlist with credentials. Wildcard `*` is forbidden with credentials, and configuration must fail closed rather than silently widen access.

## Configuration, privacy and logging

Secrets live in ignored local `.env` or deployed secrets, never Git, browser configuration or CI logs. Examples contain no functional credentials. Log request/correlation IDs, outcome/error categories and timing as needed; do not log passwords, tokens, connection strings, medical messages/documents or complete profiles. Redact exception paths and external provider errors.

Send only required features to AI, and necessary user context plus approved assessment evidence to Agent. External provider retention, region, cost and data-use settings require an explicit decision before real user content is sent. Use synthetic data for demos/tests. Minimum account age is 18; younger users are unsupported in this MVP. `sex_at_birth` is optional and sensitive, with no inference from other profile fields. Conversation retention is 30 days for the prototype and user deletion is required. Account deletion/export and operational deletion details remain pending their implementation tickets. Do not claim guardian controls exist.

Backend-to-service calls use distinct opaque bearer credentials; provisioning/rotation and network reachability remain **PENDING HS-016**. AI/Agent endpoints are not public alternatives to the application API. Validate upstream and downstream schemas and bound payloads. Use 2-second connect/10-second total AI timeouts and 2-second connect/30-second total Agent timeouts. Do not make automatic application retries initially.

## Healthcare safety boundary

Prototype scores are experimental, not clinically validated diagnoses. Only AI produces them. Preserve model/target/version evidence; do not label service failure as low risk. Agent must communicate uncertainty, abstain when evidence is insufficient and escalate urgent signals according to reviewed product safety behavior. The backend preserves those states rather than converting them into generic success copy.

## Deferred uploads

No uploads in Stage 2 or the immediate core. When approved, define content/type/size validation, safe filenames/storage keys, ownership-protected access, content processing isolation, scanning strategy, retention and low-confidence handling. No raw documents in Git or public static hosting.

## Verification

Required tests include auth/session paths, cross-user ownership, invalid input, error redaction and downstream failure handling. Add secret/dependency scanning during runtime CI foundations; configure tools and required checks rather than claim scans exist now. Assess upload and prompt-injection paths with their feature tickets. Record residual limitations in release evidence.
