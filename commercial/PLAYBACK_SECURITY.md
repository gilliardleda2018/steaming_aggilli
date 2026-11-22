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
- Player integration, short-lived playback URLs, geographic verification,
  rate limiting, device management and DRM where contracts require it.
- Individual user consent, LGPD policies, customer support and cancellation.

Never rely on a client-supplied `subscription`, `listener`, `territory`
or `rights` object. All must be independently established server-side.

The existing public AzuraCast station and Winamp catalog remain unchanged.

## Private audio in staging

`GET` and `HEAD /listeners/playback/{track_id}` require a listener bearer
token. Every request, including a new HTTP byte range, checks the current
account, subscription and rights. Responses use `Cache-Control: private, no-store`.

Set `AGGILLI_COMMERCIAL_MEDIA_DIR` to a private, operator-managed directory
outside the web root. Place a staging MP3 at `<track_id>.mp3` using ASCII
letters, numbers, hyphens and underscores for the ID. Configure
`AGGILLI_COMMERCIAL_PLAYBACK_TERRITORY` with the staging territory (e.g. `BR`).
The server uses this value for rights decisions. Geographic verification of
the listener is still required before public commercial use.
