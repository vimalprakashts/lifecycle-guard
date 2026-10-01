# Auth (sign-up, sign-in, sessions, accounts)

## Customer / end user
- [ ] Sign up: validation, duplicate-account handling, verification (email/OTP) before active
- [ ] Sign in: every supported method (password, OTP, social/OAuth, magic link) and the order they're offered
- [ ] Forgot / reset password: time-limited single-use token, old sessions handled
- [ ] Email / phone change with re-verification
- [ ] Profile view + edit; delete / deactivate account
- [ ] Sign out (this device) and sign out everywhere

## Admin / ops
- [ ] User list: search, filter by status/role, view last login, export
- [ ] Impersonate / view-as (audited) and disable / lock an account with reason
- [ ] Role & permission assignment, permission-gated; invite new admin + accept flow
- [ ] Reset a user's MFA / force password reset

## System
- [ ] Session issue/refresh/expiry; token signature verified server-side (never decode-only)
- [ ] Token carries identity + tenant + role; cross-tenant replay rejected
- [ ] Rate limit + lockout on repeated failed logins; unlock path
- [ ] Verification / reset tokens expire and are single-use
- [ ] Cleanup job for expired tokens and stale sessions

## Edge cases
- [ ] Same email signs up twice / email already taken
- [ ] OTP: resend throttle, expiry, wrong-code lockout, idempotent verify
- [ ] Account disabled mid-session → next request rejected
- [ ] Concurrent logins across devices; refresh-token rotation / reuse detection
- [ ] Unverified user tries to act; partial-registration resume
- [ ] Role changed mid-session → new permissions reflected within a bounded time

## Security
- [ ] Passwords hashed (bcrypt/argon2), never logged; generic "invalid credentials" (no user enumeration)
- [ ] MFA / 2FA path where required; brute-force protection
- [ ] Permission check per action AND tenant isolation per query (no IDOR on user ids)
- [ ] Secrets/keys in config; audit every auth-state change (login, lockout, role change, reset)

## Learned
