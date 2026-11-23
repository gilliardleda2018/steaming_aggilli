#!/usr/bin/env bash
# Assistente para ligar a DJ ANI (Claude) na API comercial em homologação.
#   sudo bash scripts/configure-ani-staging.sh
# Pergunta só a chave da API da Anthropic (sem eco) e o modelo (Enter usa o
# atual), grava o arquivo de credenciais (root:root 0600), reinicia o serviço
# e faz uma chamada real de teste. A chave nunca aparece na tela.
set -Eeuo pipefail
umask 077

readonly env_file=/etc/aggilli-music/commercial-staging.env
readonly service=aggilli-commercial-staging.service
readonly base=/opt/aggilli-commercial
readonly default_model=claude-opus-5-5

if (( EUID != 0 )); then echo 'Execute com sudo.' >&2; exit 1; fi
[[ -f $env_file ]] || { echo "Instale antes: scripts/install-commercial-staging.sh" >&2; exit 1; }
"$base/venv/bin/python" -c 'import anthropic' 2>/dev/null ||
  { echo "Atualize a API antes: scripts/install-commercial-staging.sh <commit>" >&2; exit 1; }

current() { sed -n "s/^$1=//p" "$env_file" | tail -n 1; }

echo 'DJ ANI com Claude (homologação). Ctrl+C cancela sem alterar nada.'
old_model=$(current AGGILLI_ANI_MODEL)
read -r -p "Modelo [Enter usa ${old_model:-$default_model}]: " model
model=${model:-${old_model:-$default_model}}
old_key=$(current ANTHROPIC_API_KEY)
read -r -s -p "Chave da API da Anthropic (sk-ant-…)${old_key:+ [Enter mantém a atual]}: " key; echo
key=${key:-$old_key}

[[ $model =~ ^[a-z0-9][a-z0-9.-]{2,63}$ ]] || { echo 'Nome de modelo inválido.' >&2; exit 2; }
[[ $key == sk-ant-* && $key != *[[:space:]]* ]] ||
  { echo 'A chave deve começar com sk-ant- e não ter espaços.' >&2; exit 2; }

backup="$env_file.backup-$(date +%Y%m%d-%H%M%S)"
cp -p -- "$env_file" "$backup"
tmp=$(mktemp "$env_file.XXXXXX")
trap 'rm -f -- "$tmp"' EXIT
grep -vE '^(AGGILLI_ANI_(ENABLED|PROVIDER|MODEL)|ANTHROPIC_API_KEY)=' "$env_file" >"$tmp" || true
printf 'AGGILLI_ANI_ENABLED=true\nAGGILLI_ANI_PROVIDER=anthropic\nAGGILLI_ANI_MODEL=%s\nANTHROPIC_API_KEY=%s\n' \
  "$model" "$key" >>"$tmp"
chown root:root "$tmp"; chmod 0600 "$tmp"
mv -f -- "$tmp" "$env_file"
trap - EXIT
unset key old_key

systemctl restart "$service"
sleep 2
systemctl is-active --quiet "$service" ||
  { echo "O serviço não iniciou. Backup em $backup. Veja: journalctl -u $service" >&2; exit 1; }

echo "Credenciais gravadas e serviço reiniciado. Testando uma chamada real ao $model…"
PYTHONPATH=$base/current "$base/venv/bin/python" - "$env_file" <<'PY'
import os, sys
for line in open(sys.argv[1], encoding="utf-8"):
    name, sep, value = line.rstrip("\n").partition("=")
    if sep and (name.startswith("AGGILLI_") or name == "ANTHROPIC_API_KEY"):
        os.environ[name] = value
import anthropic
from commercial.ani_dj import claude_intent, resolve_intent
prompt = "30 minutos para relaxar à noite"
result = resolve_intent(prompt, model_enabled=True)
print("Resultado:", result)
if result["engine"] == "ani":
    print("ANI VALIDADA: engine=ani")
else:
    try:
        claude_intent(prompt, model=os.environ["AGGILLI_ANI_MODEL"])
    except anthropic.AuthenticationError:
        print("A Anthropic recusou a chave (401). Confira a chave e rode o assistente de novo.")
    except anthropic.PermissionDeniedError:
        print("A chave não tem permissão para este modelo (403).")
    except anthropic.NotFoundError:
        print("Modelo não encontrado (404). Confira o nome do modelo.")
    except anthropic.RateLimitError:
        print("Limite de uso ou créditos esgotados (429). Confira o plano em console.anthropic.com.")
    except anthropic.APIConnectionError:
        print("Sem conexão com a API da Anthropic a partir do servidor.")
    except Exception as error:  # tipo apenas; a chave nunca é impressa
        print(f"A chamada falhou ({type(error).__name__}).")
    print("O DJ continua funcionando com a seleção local (engine=offline).")
PY
