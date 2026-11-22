# Aggilli Music — commercial streaming readiness (isolated prototype)

This module is deliberately NOT connected to the existing Winamp, AzuraCast,
Nextcloud sync, upload endpoints, or public media catalog.

## Findings
- Current player reads an AzuraCast On-Demand catalog; no per-track commercial rights metadata is present.
- Existing upload and Nextcloud synchronization do not verify distribution rights.
- Android app is a WebView wrapper; no subscriptions, accounts or DRM yet.
- Do not infer rights from uploaded media, filenames, playlist membership or ECAD registration.

## First delivery
`commercial/rights.py` is a fail-closed eligibility filter for a **future**
commercial catalog: approval, interactive streaming scope, recording and
composition rights, territories, effective dates and agreement reference.
Tests use synthetic examples, never claim real songs are licensed.

## Before public commercial launch
1. Obtain contracts/permissions covering on-demand interactive streaming for
   recordings and compositions, territory, term, remuneration, reporting and
   any offline downloads. Verify ECAD public performance obligations separately.
2. Establish a protected rights registry with signed agreement references,
   approval audit trail, revocation, and an administrative workflow.
3. Enforce rights at server-side catalog **and media playback authorization**;
   a filtered UI alone does not secure raw AzuraCast endpoints.
4. Add authenticated accounts, entitlements, subscription payments, access
   control, logging, privacy/LGPD and billing reconciliation.
5. Use a separately provisioned staging station and sample content with
   explicit permission. Never expose existing station media as commercially licensed.

No production configuration, playlists, existing catalog or DNS is modified
by this change.
