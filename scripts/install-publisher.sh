#!/usr/bin/env bash
# Instalação única do publicador automatizado. Execute com:
#   sudo bash scripts/install-publisher.sh
# Depois disso, o usuário gilliard publica com
#   sudo -n /usr/local/sbin/aggilli-publish-player <commit>
# sem senha, e somente esse comando fica liberado.
set -Eeuo pipefail

readonly user=gilliard
readonly here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
readonly sudoers=/etc/sudoers.d/aggilli-publish-player

if (( EUID != 0 )); then
  echo 'Execute com sudo.' >&2
  exit 1
fi

install -d -m 0755 -o root -g root /usr/local/lib/aggilli
install -m 0755 -o root -g root "$here/publish-player.sh" /usr/local/lib/aggilli/publish-player.sh
install -m 0755 -o root -g root "$here/aggilli-publish-player" /usr/local/sbin/aggilli-publish-player

rule="$user ALL=(root) NOPASSWD: /usr/local/sbin/aggilli-publish-player"
tmp=$(mktemp)
trap 'rm -f -- "$tmp"' EXIT
printf '%s\n' "$rule" >"$tmp"
visudo -cf "$tmp" >/dev/null
install -m 0440 -o root -g root "$tmp" "$sudoers"
visudo -c >/dev/null

echo 'Publicador instalado:'
ls -l /usr/local/sbin/aggilli-publish-player /usr/local/lib/aggilli/publish-player.sh "$sudoers"
