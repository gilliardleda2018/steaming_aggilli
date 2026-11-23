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

## Claude como motor da DJ ANI (homologação, 2026-11-23)
- `AGGILLI_ANI_PROVIDER=anthropic` usa o SDK oficial da Anthropic (`anthropic==2.12.0`)
  com `AGGILLI_ANI_MODEL=claude-opus-5-5` e `ANTHROPIC_API_KEY`.
- A resposta é limitada por saída estruturada (JSON Schema com `mood` entre os
  cinco climas do player e `title`), esforço `low` e `fallbacks: "default"`
  (outro modelo responde se o Claude recusar o pedido).
- Só o texto do pedido vai para o modelo; histórico, catálogo e dados do ouvinte não.
- Qualquer falha (chave, rede, recusa, JSON fora do esquema) mantém a seleção local
  (`engine=offline`). Configure com `sudo bash scripts/configure-ani-staging.sh`.

## Google Gemini (plano gratuito) como motor da DJ ANI
- `AGGILLI_ANI_PROVIDER=openai-compatible` com
  `AGGILLI_ANI_CHAT_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`,
  a chave do Google AI Studio em `AGGILLI_ANI_API_KEY` e um modelo Gemini Flash.
- O assistente `scripts/configure-ani-staging.sh` (opção 1) lista os modelos liberados
  para a chave e sugere um Flash estável.
- No plano gratuito o Google pode usar os pedidos para melhorar os modelos; só o texto
  do pedido musical é enviado.
