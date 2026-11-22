# Commercial playback authorization — staging policy

`entitlements.py` implements a **pure, fail-closed decision function** for
commercial interactive playback. It has no network calls and cannot expose
AzuraCast files.

Inputs must come from server-verified identity, billing and rights records:
- Listener exists and is active.
- Subscription belongs to listener, has an eligible plan and is active/trialing.
- Server-managed access expiry is in the future.
- Track has explicit interactive streaming rights for the requested territory,
  including recording and composition clearances, within the agreement period.

## Not implemented yet
- Account registration, secure password hashing or OAuth/OIDC identity.
- Billing checkout, webhook verification and subscription persistence.
- Server-side enforcement at **every** media request, byte range and download.
- Secure playback gateway / short-lived scoped URLs, geo/territory validation,
  rate limiting, device management and DRM where contracts require it.
- Individual user consent, LGPD policies, customer support and cancellation.

Never rely on a client-supplied `subscription`, `listener`, `territory`
or `rights` object. All must be independently established server-side.

The existing public AzuraCast station and Winamp catalog remain unchanged.
