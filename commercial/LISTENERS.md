# Aggilli Music Commercial — listener staging

This is a standalone **development prototype**, not a production identity or
billing service. No existing radio, player, Nextcloud or AzuraCast configuration
is modified.

## Delivered
- SQLite listener registration with PBKDF2-HMAC-SHA256 salted password hashes.
- Short-lived random bearer sessions, stored as SHA-256 digests, logout and
  server-side expiration.
- Subscription records with explicit plan/status/expiry.
- Rights-aware entitlement checks using the separately built rights registry.
- Administrative subscription endpoint requiring an independent 32+ character
  bearer secret. **It is a staging fixture, not a billing webhook.**
- Tests for login, invalid credentials, logout, missing licenses, territorial
  restrictions and admin-only subscription management.

## Do not expose this service publicly yet
Before production: OIDC or audited authentication provider, email verification,
password recovery, login throttling, MFA for admins, privacy policy and LGPD
handling, subscription billing with signed webhook verification, event
idempotency, refund/cancellation handling, transaction audit logs, anti-fraud,
backup and restore testing, TLS and hardened deployment. Never let a listener
claim a subscription through client-supplied fields.

Most importantly, **the existing AzuraCast media endpoints remain public**.
This prototype's `/listeners/access/{track_id}` endpoint only returns a
decision. It does not protect the audio itself. Commercial playback requires
an independent server-side authorized media gateway and appropriate licenses.

## Local test
```sh
python3 -m pip install fastapi httpx python-multipart bcrypt
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
