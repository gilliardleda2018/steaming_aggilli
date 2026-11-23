#!/usr/bin/env bash
# Instalação única do cabeçalho Cache-Control do player. Execute com:
#   sudo bash scripts/install-player-cache.sh
# Valida a configuração antes de recarregar o Apache (graceful, sem derrubar
# conexões da rádio) e desfaz tudo se o teste ou a verificação falharem.
set -Eeuo pipefail

readonly here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly name=aggilli-music-player-cache
readonly target=/etc/apache2/conf-available/$name.conf
readonly url=http://127.0.0.1:8100/music/

if (( EUID != 0 )); then
  echo 'Execute com sudo.' >&2
  exit 1
fi

rollback() {
  echo 'Falha: removendo a configuração e recarregando o Apache anterior.' >&2
  a2disconf -q "$name" >/dev/null 2>&1 || true
  rm -f -- "$target"
  apache2ctl -t >/dev/null 2>&1 && systemctl reload apache2 || true
}

a2enmod -q headers >/dev/null
install -m 0644 -o root -g root "$here/../infra/apache/$name.conf" "$target"
a2enconf -q "$name" >/dev/null
if ! apache2ctl -t; then rollback; exit 1; fi
systemctl reload apache2
sleep 1

headers=$(curl --fail --silent --show-error --max-time 10 -D - -o /dev/null "$url")
if ! grep -qi '^cache-control: no-cache' <<<"$headers"; then rollback; exit 1; fi
for path in catalogo.json aggilli-music-logo.jpg; do
  curl --fail --silent --max-time 10 -o /dev/null "$url$path" || { rollback; exit 1; }
done

echo 'Cache-Control do player instalado:'
grep -i '^cache-control' <<<"$headers"
