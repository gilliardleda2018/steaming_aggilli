# DJ ANI — first conversational integration (staging only)

## Delivered
- `commercial/ani_dj.py`: structured mood/title interpretation via an optional
  ANI-compatible HTTPS chat endpoint, with 8-second timeout and offline fallback.
- `commercial/intelligence.py`: deterministic licensed-track ranking, diversity,
  recent-history handling and short explanations.
- `POST /listeners/dj/session`: authenticated, premium-only staging API that
  reads a separately provisioned commercial catalog snapshot and the rights
  registry server-side. No raw playback URLs are returned.
- Tests: structured model output, injection-like invalid output, fallback,
  territory, missing rights, missing catalog and subscription access.

## Opt-in environment (do not configure in production yet)
- `AGGILLI_ANI_ENABLED=true`
- `AGGILLI_ANI_CHAT_URL=https://<approved-host>/v1/chat/completions`
- `AGGILLI_ANI_API_KEY` (secret, never committed)
- `AGGILLI_ANI_MODEL` (provider-supported model name)
- `AGGILLI_COMMERCIAL_CATALOG_FILE` (trusted JSON snapshot, not the public
  AzuraCast library by default)

The existing ANI endpoint may not support the `model` parameter or the
OpenAI-compatible response format exactly; validate against a staging endpoint
before enabling it. Never send listening history, personal data or the full
music catalog to the LLM. A model cannot authorize streaming or grant a plan.

## Not yet implemented
- Real AI-powered player UI and playback service.
- Secure streaming gateway, protected byte ranges, DRM or offline downloads.
- Verified payment events, full identity hardening and rights holder reporting.
- Production-grade model output safety, rate limits, budget and abuse controls.

The original Winamp, Android player, Nextcloud, AzuraCast and DNS are unchanged.
