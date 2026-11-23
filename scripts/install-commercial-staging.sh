#!/usr/bin/env bash
# Instala ou atualiza a API comercial em HOMOLOGAÇÃO a partir de um commit da
# branch de trabalho. Execute com:
#   sudo bash scripts/install-commercial-staging.sh <commit>
# Não altera o player, o catálogo, a rádio nem a sincronização. A ANI fica
# desligada até você preencher /etc/aggilli-music/commercial-staging.env.
set -Eeuo pipefail
umask 022

readonly repo=/opt/aggilli-deploy/steaming_aggilli
readonly repo_url=https://github.com/gilliardleda2018/steaming_aggilli.git
readonly branch=feat/nextcloud-webdav-sync
readonly base=/opt/aggilli-commercial
readonly user=aggilli-commercial
readonly env_file=/etc/aggilli-music/commercial-staging.env
readonly conf=aggilli-music-commercial-staging
readonly health=http://127.0.0.1:8100/music/commercial-api/health

if (( EUID != 0 )); then echo 'Execute com sudo.' >&2; exit 1; fi
revision=${1:-}
[[ $revision =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Uso: install-commercial-staging.sh <commit>' >&2; exit 2; }

if [[ ! -d $repo/.git ]]; then git clone --quiet --branch "$branch" "$repo_url" "$repo"; fi
git -C "$repo" fetch --quiet origin "$branch"
commit=$(git -C "$repo" rev-parse --verify --quiet "$revision^{commit}") ||
  { echo "Commit $revision não encontrado." >&2; exit 3; }
git -C "$repo" merge-base --is-ancestor "$commit" "origin/$branch" ||
  { echo "Commit $commit não pertence a origin/$branch." >&2; exit 3; }
show() { git -C "$repo" show "$commit:$1"; }

# Usuário de sistema sem login e sem pasta pessoal.
getent passwd "$user" >/dev/null ||
  useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$user"

# Dependências fixas num ambiente próprio.
install -d -m 0755 "$base" "$base/releases"
[[ -x $base/venv/bin/python ]] || python3 -m venv "$base/venv"
show infra/commercial/requirements.txt >"$base/requirements.txt"
"$base/venv/bin/python" -m pip install --quiet --disable-pip-version-check -r "$base/requirements.txt"

# Código: somente o pacote commercial/ do commit.
stage=$(mktemp -d "$base/releases/.stage-XXXXXX")
chmod 0755 "$stage"
trap 'rm -rf -- "$stage"' EXIT
install -d -m 0755 "$stage/commercial"
for file in $(git -C "$repo" ls-tree --name-only "$commit" commercial/ | grep '\.py$'); do
  show "$file" >"$stage/$file"
  chmod 0644 "$stage/$file"
done
[[ -f $stage/commercial/__init__.py ]] || : >"$stage/commercial/__init__.py"
PYTHONPATH=$stage "$base/venv/bin/python" -c 'import commercial.listener_api'
find "$stage" -name __pycache__ -prune -exec rm -rf {} +
rm -rf -- "$base/releases/$commit"
mv -T "$stage" "$base/releases/$commit"
trap - EXIT
if [[ -L $base/current ]]; then ln -sfn "$(readlink -f "$base/current")" "$base/previous"; fi
ln -sfn "$base/releases/$commit" "$base/current.new"
mv -Tf "$base/current.new" "$base/current"

# Credenciais: criadas vazias uma única vez; nunca sobrescritas.
install -d -m 0755 /etc/aggilli-music
if [[ ! -e $env_file ]]; then
  show infra/commercial/commercial-staging.env.example >"$env_file"
  chown root:root "$env_file"
  chmod 0600 "$env_file"
fi

for unit in aggilli-commercial-staging.socket aggilli-commercial-staging.service; do
  show "infra/commercial/$unit" >"/etc/systemd/system/$unit"
  chmod 0644 "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --quiet --now aggilli-commercial-staging.socket
systemctl try-restart aggilli-commercial-staging.service

# Rota no Apache, com teste e desfazimento.
rollback_apache() {
  echo 'Falha: removendo a rota da API comercial.' >&2
  a2disconf -q "$conf" >/dev/null 2>&1 || true
  rm -f -- "/etc/apache2/conf-available/$conf.conf"
  apache2ctl -t >/dev/null 2>&1 && systemctl reload apache2 || true
}
a2enmod -q proxy proxy_http >/dev/null
show "infra/apache/$conf.conf" >"/etc/apache2/conf-available/$conf.conf"
chmod 0644 "/etc/apache2/conf-available/$conf.conf"
a2enconf -q "$conf" >/dev/null
if ! apache2ctl -t; then rollback_apache; exit 1; fi
systemctl reload apache2
sleep 2

if ! curl --fail --silent --show-error --max-time 15 "$health" | grep -q '"commercial-staging"'; then
  rollback_apache
  systemctl disable --quiet --now aggilli-commercial-staging.socket || true
  systemctl stop aggilli-commercial-staging.service || true
  echo 'A API não respondeu. Consulte: journalctl -u aggilli-commercial-staging.service' >&2
  exit 1
fi
for path in /music/ /music/catalogo.json; do
  curl --fail --silent --max-time 10 -o /dev/null "http://127.0.0.1:8100$path" ||
    { echo "Atenção: $path deixou de responder." >&2; exit 1; }
done

echo "API comercial em homologação: $commit"
echo "Saúde: $(curl --silent --max-time 10 "$health")"
grep -q '^AGGILLI_ANI_ENABLED=true' "$env_file" &&
  echo 'ANI: habilitada no arquivo de credenciais.' ||
  echo "ANI: desligada. Preencha $env_file com sudoedit e reinicie o serviço."
