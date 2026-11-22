#!/usr/bin/env bash
# Aggilli Music unified player preview — never overwrite the production player.
set -Eeuo pipefail
REPO="/home/gilliard/projetos/steaming_aggilli"
SOURCE="$REPO/player/index.html"
LIVE="/var/www/aggilli-music"
PREVIEW="/var/www/aggilli-music-preview"
PORT="${AGGILLI_PREVIEW_PORT:-8765}"

if [[ $(id -u) -ne 0 ]]; then echo "Execute como root." >&2; exit 1; fi
if [[ ! -f "$SOURCE" || ! -f "$LIVE/catalogo.json" ]]; then
  echo "Faltam player/index.html ou catálogo em $LIVE. Nada foi alterado." >&2; exit 1
fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1024 || PORT > 65535 )); then
  echo "Porta de prévia inválida." >&2; exit 1
fi
if [[ -e "$PREVIEW" && ! -d "$PREVIEW" ]]; then
  echo "O caminho de prévia já existe e não é diretório." >&2; exit 1
fi
install -d -m 0755 "$PREVIEW"
install -m 0644 "$SOURCE" "$PREVIEW/index.html"
for item in catalogo.json generos.json duracoes.json; do
  if [[ -f "$LIVE/$item" ]]; then
    install -m 0644 "$LIVE/$item" "$PREVIEW/$item"
  fi
done
cat > "$PREVIEW/LEIA-ME.txt" <<'TXT'
Prévia visual isolada. O catálogo é uma cópia do índice público.
As rotas de streaming e upload NÃO são replicadas: a reprodução pode falhar.
A rádio, a sincronização e o player de produção não são modificados.
TXT
echo "Prévia criada em $PREVIEW"
echo "Para visualização local somente, execute:"
echo "cd $PREVIEW && python3 -m http.server $PORT --bind 127.0.0.1"
echo "No navegador do servidor, abra http://127.0.0.1:$PORT/"
echo "Se estiver em outra máquina, use um túnel SSH seguro para a porta $PORT."
echo "A prévia não reproduz necessariamente áudio; produção permanece intacta."
