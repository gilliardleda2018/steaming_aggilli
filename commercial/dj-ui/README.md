# DJ ANI UI — standalone staging preview

This responsive page is an **independent preview**, not a replacement for
the existing Aggilli Music player. It requests licensed recommendations from
`POST /listeners/dj/session` using a staging listener bearer token.

- No audio playback or unlicensed music is exposed.
- No token is stored in localStorage, cookies or a URL.
- User/model strings are rendered as text, never injected as HTML.
- Host the UI and API on the **same HTTPS origin** with a reverse proxy
  before real testing. Cross-origin access requires explicitly reviewed CORS.
- Do not use production AzuraCast credentials, public radio media endpoints
  or real user information during initial testing.
- The DJ ANI model adapter is optional; offline fallback remains available.

Future: native Android media session, listening controls, protected stream
gateway, cover art, transitions, playback queue and opt-in personalization.
