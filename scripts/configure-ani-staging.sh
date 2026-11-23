#!/usr/bin/env bash
# Assistente para ligar a DJ ANI na API comercial em homologação.
#   sudo bash scripts/configure-ani-staging.sh gemini   (vai direto ao Gemini)
#   sudo bash scripts/configure-ani-staging.sh   (ou, como root, sem sudo)
# 1 = Google Gemini (plano gratuito, endpoint compatível com OpenAI)
# 2 = Claude (Anthropic, SDK oficial; exige créditos)
# Pergunta a chave sem eco, sugere o modelo, grava o arquivo de credenciais
# (root:root 0600), reinicia o serviço e faz uma chamada real de teste.
# A chave nunca aparece na tela nem na saída.
set -Eeuo pipefail
umask 077

readonly env_file=/etc/aggilli-music/commercial-staging.env
readonly service=aggilli-commercial-staging.service
readonly base=/opt/aggilli-commercial
readonly py=$base/venv/bin/python
readonly gemini_url=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
readonly claude_model=claude-opus-5-5

if (( EUID != 0 )); then echo 'Execute como root (sudo ou su -).' >&2; exit 1; fi
[[ -f $env_file ]] || { echo "Instale antes: scripts/install-commercial-staging.sh" >&2; exit 1; }

current() { sed -n "s/^$1=//p" "$env_file" | tail -n 1; }

echo 'DJ ANI (homologação). Ctrl+C cancela sem alterar nada.'
old_provider=$(current AGGILLI_ANI_PROVIDER)
# O provedor pode vir como argumento (gemini | claude); sem argumento, pergunta e o padrão é o Gemini.
case ${1:-} in
  gemini) choice=1 ;;
  claude) choice=2 ;;
  '') read -r -p "Provedor: 1 = Google Gemini (grátis), 2 = Claude [Enter usa 1]: " choice
      choice=${choice:-1} ;;
  *) echo 'Uso: configure-ani-staging.sh [gemini|claude]' >&2; exit 2 ;;
esac
[[ $choice == 1 ]] && echo 'Provedor: Google Gemini'
[[ $choice == 2 ]] && echo 'Provedor: Claude'

if [[ $choice == 1 ]]; then
  provider=openai-compatible
  key_name=AGGILLI_ANI_API_KEY
  old_key=$( [[ $(current AGGILLI_ANI_CHAT_URL) == "$gemini_url" ]] && current AGGILLI_ANI_API_KEY || true )
  read -r -s -p "Chave da API do Gemini (aistudio.google.com)${old_key:+ [Enter mantém a atual]}: " key; echo
  key=${key:-$old_key}
  [[ -n $key && $key != *[[:space:]]* ]] || { echo 'Chave vazia ou com espaços.' >&2; exit 2; }
  echo 'Buscando os modelos liberados para esta chave…'
  suggested=$(GEMINI_KEY=$key "$py" - <<'PY'
import os, sys, httpx
try:
    r = httpx.get("https://generativelanguage.googleapis.com/v1beta/openai/models",
                  headers={"Authorization": "Bearer " + os.environ["GEMINI_KEY"]}, timeout=15)
except httpx.HTTPError as error:
    sys.exit(f"Sem conexão com o Gemini ({type(error).__name__}).")
if r.status_code != 200:
    sys.exit(f"O Gemini recusou a chave (HTTP {r.status_code}).")
names = sorted({m["id"].removeprefix("models/") for m in r.json().get("data", []) if "id" in m})
skip = ("lite", "image", "tts", "live", "audio", "embedding", "exp", "preview", "thinking", "vision")
flash = [n for n in names if "gemini" in n and "flash" in n and not any(s in n for s in skip)]
print((flash or [n for n in names if "gemini" in n] or [""])[-1])
PY
  ) || exit 2
  old_model=$(current AGGILLI_ANI_MODEL)
  [[ $old_provider == openai-compatible && -n $old_model ]] || old_model=$suggested
  read -r -p "Modelo [Enter usa ${old_model:-nenhum encontrado}]: " model
  model=${model:-$old_model}
  url=$gemini_url
elif [[ $choice == 2 ]]; then
  provider=anthropic
  key_name=ANTHROPIC_API_KEY
  old_key=$(current ANTHROPIC_API_KEY)
  read -r -s -p "Chave da API da Anthropic (sk-ant-…)${old_key:+ [Enter mantém a atual]}: " key; echo
  key=${key:-$old_key}
  [[ $key == sk-ant-* && $key != *[[:space:]]* ]] ||
    { echo 'A chave deve começar com sk-ant- e não ter espaços.' >&2; exit 2; }
  old_model=$(current AGGILLI_ANI_MODEL)
  [[ $old_provider == anthropic && -n $old_model ]] || old_model=$claude_model
  read -r -p "Modelo [Enter usa $old_model]: " model
  model=${model:-$old_model}
  url=$(current AGGILLI_ANI_CHAT_URL)
else
  echo 'Escolha 1 ou 2.' >&2; exit 2
fi
[[ $model =~ ^[a-z0-9][a-z0-9._-]{2,63}$ ]] || { echo 'Nome de modelo inválido.' >&2; exit 2; }

backup="$env_file.backup-$(date +%Y%m%d-%H%M%S)"
cp -p -- "$env_file" "$backup"
tmp=$(mktemp "$env_file.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT
grep -vE "^(AGGILLI_ANI_(ENABLED|PROVIDER|MODEL|CHAT_URL)|$key_name)=" "$env_file" >"$tmp" || true
printf 'AGGILLI_ANI_ENABLED=true\nAGGILLI_ANI_PROVIDER=%s\nAGGILLI_ANI_MODEL=%s\nAGGILLI_ANI_CHAT_URL=%s\n%s=%s\n' \
  "$provider" "$model" "$url" "$key_name" "$key" >>"$tmp"
chown root:root "$tmp"; chmod 0600 "$tmp"
mv -f -- "$tmp" "$env_file"
trap - EXIT
unset key old_key

systemctl restart "$service"
sleep 2
systemctl is-active --quiet "$service" ||
  { echo "O serviço não iniciou. Backup em $backup. Veja: journalctl -u $service" >&2; exit 1; }

echo "Credenciais gravadas e serviço reiniciado. Testando uma chamada real ao $model…"
PYTHONPATH=$base/current "$py" - "$env_file" <<'PY'
import os, sys
for line in open(sys.argv[1], encoding="utf-8"):
    name, sep, value = line.rstrip("\n").partition("=")
    if sep and (name.startswith("AGGILLI_") or name == "ANTHROPIC_API_KEY"):
        os.environ[name] = value
secrets = [v for v in (os.environ.get("AGGILLI_ANI_API_KEY"), os.environ.get("ANTHROPIC_API_KEY")) if v]
def masked(text):
    for secret in secrets:
        text = text.replace(secret, "***")
    return text[:400]

import httpx
from commercial.ani_dj import ani_intent, claude_intent, resolve_intent
prompt = "30 minutos para relaxar à noite"
result = resolve_intent(prompt, model_enabled=True)
print("Resultado:", result)
if result["engine"] == "ani":
    print("ANI VALIDADA: engine=ani")
    sys.exit(0)
try:
    if os.environ.get("AGGILLI_ANI_PROVIDER") == "anthropic":
        claude_intent(prompt, model=os.environ["AGGILLI_ANI_MODEL"])
    else:
        ani_intent(prompt, endpoint=os.environ["AGGILLI_ANI_CHAT_URL"],
                   token=os.environ["AGGILLI_ANI_API_KEY"], model=os.environ["AGGILLI_ANI_MODEL"])
except httpx.HTTPStatusError as error:
    print(f"O provedor recusou o pedido (HTTP {error.response.status_code}): {masked(error.response.text)}")
except Exception as error:
    print(f"A chamada falhou ({type(error).__name__}: {masked(str(getattr(error, 'message', error)))})")
print("O DJ continua funcionando com a seleção local (engine=offline).")
PY
