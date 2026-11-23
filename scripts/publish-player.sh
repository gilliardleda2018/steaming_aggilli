#!/usr/bin/env bash
# Publish the static player through the existing Debian Apache route.
set -Eeuo pipefail

revision=${1:?Informe o commit do player a publicar.}
live=/var/www/aggilli-music
origin=http://127.0.0.1:8100
host=server.taila400aa.ts.net
asset=aggilli-music-logo.jpg

if (( EUID != 0 )); then
  echo 'Execute como root, a partir do repositório no Debian.' >&2
  exit 1
fi
if [[ ! -f "$live/index.html" || ! -f "$live/catalogo.json" ]]; then
  echo "Player ou catálogo ausente em $live. Publicação cancelada." >&2
  exit 1
fi

work=$(mktemp -d)
stage=$(mktemp -d "$live/.publish-XXXXXX")
changed=0
backup=
fetch() {
  curl --fail --silent --show-error --max-time 12 -H "Host: $host" "$@"
}
rollback() {
  local status=$?
  if (( changed )); then
    echo "Falha após a instalação. Restaurando arquivos de $backup." >&2
    cp -p -- "$backup/index.html" "$stage/restore.html"
    mv -f -- "$stage/restore.html" "$live/index.html"
    if [[ -f "$backup/$asset" ]]; then
      cp -p -- "$backup/$asset" "$stage/$asset"
      mv -f -- "$stage/$asset" "$live/$asset"
    else
      rm -f -- "$live/$asset"
    fi
  fi
  rm -rf -- "$work" "$stage"
  return "$status"
}
trap rollback EXIT

git show "$revision:player/index.html" >"$work/index.html"
git show "$revision:player/$asset" >"$work/$asset"
for marker in 'id="clipToggle"' 'id="aggilliVolume"' 'id="aggilliEq16000"' 'id="library"'; do
  grep -Fq "$marker" "$work/index.html" ||
    { echo "Revisão sem o controle esperado: $marker" >&2; exit 1; }
done

fetch "$origin/music/" -o "$work/current.html"
cmp -s -- "$work/current.html" "$live/index.html" ||
  { echo 'O Apache entregou um index.html diferente do arquivo local. Publicação cancelada.' >&2; exit 1; }
fetch "$origin/music/catalogo.json" -o "$work/catalog.json"
python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(data, list) else 1)' "$work/catalog.json"

radio_content_type() {
  local type
  type=$(fetch -I --output /dev/null --write-out '%{content_type}' "$1" 2>/dev/null) || type=
  if [[ $type != audio/* ]]; then
    # Some streaming servers answer GET but not HEAD. Limit the probe to two seconds.
    type=$(curl --silent --max-time 2 --range 0-0 --output /dev/null \
      --write-out '%{http_code} %{content_type}' -H "Host: $host" "$1") || true
    case $type in
      '200 'audio/*|'206 'audio/*) type=${type#* } ;;
      *) type= ;;
    esac
  fi
  printf '%s' "$type"
}
radio_type=$(radio_content_type "$origin/music/radio.mp3")
if [[ $radio_type != audio/* ]]; then
  radio_type=$(radio_content_type "$origin/radio.mp3")
  if [[ $radio_type != audio/* ]]; then
    echo 'Nenhuma das rotas de rádio respondeu com áudio. Publicação cancelada.' >&2
    exit 1
  fi
  sed -i "s|audio.src='radio.mp3';|audio.src='/radio.mp3';|" "$work/index.html"
fi

install -d -m 0700 /var/backups/aggilli-music
backup=$(mktemp -d /var/backups/aggilli-music/player-XXXXXXXX)
cp -p -- "$live/index.html" "$backup/index.html"
if [[ -f "$live/$asset" ]]; then cp -p -- "$live/$asset" "$backup/$asset"; fi
install -m 0644 "$work/$asset" "$stage/$asset"
install -m 0644 "$work/index.html" "$stage/index.html"

changed=1
mv -f -- "$stage/$asset" "$live/$asset"
mv -f -- "$stage/index.html" "$live/index.html"
fetch "$origin/music/" -o "$work/published.html"
fetch "$origin/music/$asset" -o "$work/published-logo.jpg"
cmp -- "$work/index.html" "$work/published.html"
cmp -- "$work/$asset" "$work/published-logo.jpg"
changed=0
printf 'Player confirmado pelo Apache. Backup: %s\n' "$backup"
printf 'https://%s/music/\n' "$host"
