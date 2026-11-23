#!/usr/bin/env bash
# Assistente para configurar a ANI na API comercial em homologação, sem editor.
#   sudo bash scripts/configure-ani-staging.sh
# Pergunta URL, modelo e chave (sem eco), grava o arquivo de credenciais
# (root:root 0600), reinicia o serviço e faz uma chamada real de teste.
# Nenhum valor é mostrado na tela, exceto a URL e o modelo.
set -Eeuo pipefail
umask 077

readonly env_file=/etc/aggilli-music/commercial-staging.env
readonly service=aggilli-commercial-staging.service
readonly base=/opt/aggilli-commercial

if (( EUID != 0 )); then echo 'Execute com sudo.' >&2; exit 1; fi
[[ -f $env_file ]] || { echo "Instale antes: scripts/install-commercial-staging.sh" >&2; exit 1; }

current() { sed -n "s/^$1=//p" "$env_file" | tail -n 1; }
ask() {  # ask <rótulo> <variável> — Enter mantém o valor atual
  local label=$1 name=$2 old value
  old=$(current "$name")
  read -r -p "$label${old:+ [Enter mantém: $old]}: " value
  printf '%s' "${value:-$old}"
}

echo 'Configuração da ANI (homologação). Ctrl+C cancela sem alterar nada.'
url=$(ask 'URL HTTPS do chat (…/chat/completions)' AGGILLI_ANI_CHAT_URL)
model=$(ask 'Nome do modelo' AGGILLI_ANI_MODEL)
old_key=$(current AGGILLI_ANI_API_KEY)
read -r -s -p "Chave da API${old_key:+ [Enter mantém a atual]}: " key; echo
key=${key:-$old_key}

if [[ ! $url =~ ^https://[^/@?#[:space:]]+(/[^?#[:space:]]*)?$ ]]; then
  echo 'URL inválida: use https://, sem usuário, senha, espaços, ? ou #.' >&2; exit 2
fi
[[ -n $model && $model != *[[:space:]]* ]] || { echo 'Modelo vazio ou com espaços.' >&2; exit 2; }
[[ -n $key && $key != *[[:space:]]* ]] || { echo 'Chave vazia ou com espaços.' >&2; exit 2; }

backup="$env_file.backup-$(date +%Y%m%d-%H%M%S)"
cp -p -- "$env_file" "$backup"
tmp=$(mktemp "$env_file.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT
grep -vE '^AGGILLI_ANI_(ENABLED|CHAT_URL|API_KEY|MODEL)=' "$env_file" >"$tmp" || true
printf 'AGGILLI_ANI_ENABLED=true\nAGGILLI_ANI_CHAT_URL=%s\nAGGILLI_ANI_API_KEY=%s\nAGGILLI_ANI_MODEL=%s\n' \
  "$url" "$key" "$model" >>"$tmp"
chown root:root "$tmp"; chmod 0600 "$tmp"
mv -f -- "$tmp" "$env_file"
trap - EXIT
unset key old_key

systemctl restart "$service"
sleep 2
systemctl is-active --quiet "$service" ||
  { echo "O serviço não iniciou. Backup em $backup. Veja: journalctl -u $service" >&2; exit 1; }

echo 'Credenciais gravadas e serviço reiniciado. Testando uma chamada real à ANI…'
PYTHONPATH=$base/current "$base/venv/bin/python" - "$env_file" <<'PY'
import os, sys
for line in open(sys.argv[1], encoding="utf-8"):
    name, sep, value = line.rstrip("\n").partition("=")
    if sep and name.startswith("AGGILLI_"):
        os.environ[name] = value
from commercial.ani_dj import ani_intent, resolve_intent
prompt = "30 minutos para relaxar à noite"
result = resolve_intent(prompt, model_enabled=True)
print("Resultado:", result)
if result["engine"] == "ani":
    print("ANI VALIDADA: engine=ani")
else:
    try:
        ani_intent(prompt, endpoint=os.environ["AGGILLI_ANI_CHAT_URL"],
                   token=os.environ["AGGILLI_ANI_API_KEY"], model=os.environ["AGGILLI_ANI_MODEL"])
    except Exception as error:  # só o tipo e a mensagem, nunca a chave
        detail = str(error).replace(os.environ["AGGILLI_ANI_API_KEY"], "***")[:300]
        print(f"A ANI falhou ({type(error).__name__}: {detail}).")
    print("O DJ continua funcionando com a seleção local (engine=offline).")
PY
