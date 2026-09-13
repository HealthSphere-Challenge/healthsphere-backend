# Security and privacy architecture

Status: approved requirements; authentication mechanism and provider/deployment-specific controls remain unresolved. This is product engineering guidance, not a claim of regulatory compliance.

## Trust and access

Backend authenticates requests and enforces ownership for every profile, measurement, assessment and conversation operation. One account = one profile; no guardian, delegated or multi-profile access. Client route guards are UX only. Never trust a client-provided user ID as authorization. Verify cross-user denial and missing/expired credentials in integration tests.

HS-006 must choose and record authentication/session transport, password hashing library/settings, expiration/revocation, logout and CSRF behavior. Consider secure HttpOnly cookie sessions versus token transport explicitly with the frontend and deployment constraints; neither is selected by this document. Add HTTPS, origin allowlist/CORS and request/rate limits appropriate to the chosen design. Google OAuth and password recovery are separate unapproved capabilities.

## Configuration, privacy and logging

Secrets live in ignored local `.env` or deployed secrets, never Git, browser configuration or CI logs. Examples contain no functional credentials. Log request/correlation IDs, outcome/error categories and timing as needed; do not log passwords, tokens, connection strings, medical messages/documents or complete profiles. Redact exception paths and external provider errors.

Send only required features to AI, and necessary user context plus approved assessment evidence to Agent. External provider retention, region, cost and data-use settings require an explicit decision before real user content is sent. Use synthetic data for demos/tests. Application retention, account deletion/export and minimum age/sensitive-field policy remain unresolved. Do not claim guardian controls exist.

Service authentication and network reachability are HS-002/016 decisions. AI/Agent endpoints are not public alternatives to the application API. Validate upstream and downstream schemas; bound payloads/timeouts. Avoid resource exhaustion and duplicate writes on retries.

## Healthcare safety boundary

Prototype scores are experimental, not clinically validated diagnoses. Only AI produces them. Preserve model/target/version evidence; do not label service failure as low risk. Agent must communicate uncertainty, abstain when evidence is insufficient and escalate urgent signals according to reviewed product safety behavior. The backend preserves those states rather than converting them into generic success copy.

## Deferred uploads

No uploads in Stage 2 or the immediate core. When approved, define content/type/size validation, safe filenames/storage keys, ownership-protected access, content processing isolation, scanning strategy, retention and low-confidence handling. No raw documents in Git or public static hosting.

## Verification

Required tests include auth/session paths, cross-user ownership, invalid input, error redaction and downstream failure handling. Add secret/dependency scanning during runtime CI foundations; configure tools and required checks rather than claim scans exist now. Assess upload and prompt-injection paths with their feature tickets. Record residual limitations in release evidence.
