#!/usr/bin/env bash
# Cria (opcional) uma conta de ouvinte de homologação e mostra o token de sessão
# (12 h) para colar em "Token do ouvinte" no painel DJ ANI do player.
# A senha é digitada sem eco e nunca vai para a linha de comando.
#   bash scripts/commercial-staging-login.sh            # só entrar
#   bash scripts/commercial-staging-login.sh --register # criar conta e entrar
set -Eeuo pipefail

readonly api=http://127.0.0.1:8100/music/commercial-api

read -r -p 'E-mail do ouvinte de homologação: ' email
read -r -s -p 'Senha (mínimo 12 caracteres): ' password
echo

python3 -I - "$api" "${1:-}" <<'PY' 3<<<"$email"$'\n'"$password"
import json, os, sys, urllib.error, urllib.request

api, mode = sys.argv[1], sys.argv[2]
with os.fdopen(3) as secrets_in:
    email, password = secrets_in.read().split("\n", 1)
body = json.dumps({"email": email.strip(), "password": password.rstrip("\n")}).encode()

def post(path):
    request = urllib.request.Request(api + path, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)

try:
    if mode == "--register":
        post("/listeners/register")
        print("Conta criada.")
    token = post("/listeners/login")["access_token"]
except urllib.error.HTTPError as error:
    sys.exit(f"Falhou: HTTP {error.code} {error.read().decode(errors='replace')[:200]}")

print("\nURL HTTPS da API comercial: https://server.taila400aa.ts.net/music/commercial-api")
print("Token do ouvinte (válido por 12 h, não compartilhe):")
print(token)
PY
