# Aggilli Music Intelligence — first AI-ready delivery

The `commercial/intelligence.py` module is a **deterministic, explainable
recommendation baseline**, not an LLM and not yet deployed to the player.
It interprets a small set of Portuguese listening intents (focus, relaxation,
energy, romance, discovery), ranks music by catalog metadata, reduces repeats
and diversifies artists. It emits only licensed track IDs and explanations;
it does not return raw media URLs or grant playback permission.

## Roadmap
1. Enrich licensed catalog metadata with consented tags, tempo, mood, energy,
   language and optional audio embeddings; measure quality and bias.
2. Introduce an opt-in conversational DJ backed by a provider-independent LLM
   adapter. Keep rights, territories, subscriptions and media access enforced
   by trusted server code, not model-generated text.
3. Add transparent controls for discovery preferences, history deletion,
   private listening and explicit user consent.
4. Build a new player experience in staging, with real Android background
   playback and controls; do not replace the existing Winamp until tested.
5. Add listening session transitions and safe fallback when AI is unavailable.

## Licensing boundary
Only explicit interactive streaming rights authorize recommendations.
The current AzuraCast library is **not** automatically a commercial catalog.
No model API key, paid AI provider, production integration or deployment is
configured by this module.
