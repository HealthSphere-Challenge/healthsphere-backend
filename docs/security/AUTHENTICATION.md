# Authentication and profile security

HS-006 uses Argon2id through `argon2-cffi` with time cost 3, memory cost 64 MiB, and parallelism 4. Successful authentication rehashes passwords when the configured parameters change. Passwords never enter logs and only the encoded Argon2 hash is stored.

The browser session cookie is `healthsphere_session`: a 256-bit opaque random token with `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` in production. PostgreSQL stores only its SHA-256 digest. Sessions have a seven-day absolute expiry, 24-hour idle timeout, concurrent-session support, and current-session revocation on logout.

Register and login return a separate random CSRF token and set it in the readable `healthsphere_csrf` cookie. The server stores only its digest on the matching session. The SPA copies the cookie value to `X-CSRF-Token` for state-changing requests; safe methods do not require it. A stolen CSRF token is not a session credential. CORS permits credentials only for explicit configured origins and rejects wildcards.

Profile routes derive ownership solely from the authenticated session and accept no user or profile identifier. PATCH retains omitted fields, persists `null` as unknown, and persists `[]` as explicitly none. Date of birth completes adult eligibility; account creation itself does not collect or infer age. Current weight and BMI remain future measurement projections.

Process-local throttling was rejected because it fails open across workers and restarts. A robust register/login limiter therefore remains deferred until a shared gateway or datastore is selected. Deployment must rate-limit these routes at the trusted edge in the interim; this is the main residual HS-006 security risk.
