#!/usr/bin/env bash
# Implanta o código da sincronização Nextcloud -> AzuraCast de um commit da
# branch de trabalho. Execute a cada implantação, conferindo o commit:
#   sudo bash scripts/deploy-sync-code.sh <commit>
#   sudo bash scripts/deploy-sync-code.sh --rollback
# O código roda como root, por isso a implantação exige sudo com senha.
# Os serviços passam a usar /opt/aggilli-sync/current, fora de qualquer clone
# de usuário. Nenhuma sincronização é iniciada por este script.
set -Eeuo pipefail
umask 022

readonly repo=/opt/aggilli-deploy/steaming_aggilli
readonly repo_url=https://github.com/gilliardleda2018/steaming_aggilli.git
readonly branch=feat/nextcloud-webdav-sync
readonly base=/opt/aggilli-sync
readonly files=(sync.py queue_worker.py refresh_player_catalog.py)
readonly venv_python=/opt/aggilli-nextcloud-sync-venv/bin/python

if (( EUID != 0 )); then echo 'Execute com sudo.' >&2; exit 1; fi

install_dropins() {
  install -d -m 0755 /etc/systemd/system/aggilli-nextcloud-sync.service.d /etc/systemd/system/aggilli-sync-queue.service.d
  printf '[Service]\nExecStart=\nExecStart=%s %s/current/sync.py\n' "$venv_python" "$base" \
    >/etc/systemd/system/aggilli-nextcloud-sync.service.d/10-aggilli-sync-code.conf
  printf '[Service]\nExecStart=\nExecStart=/usr/bin/python3 %s/current/queue_worker.py\n' "$base" \
    >/etc/systemd/system/aggilli-sync-queue.service.d/10-aggilli-sync-code.conf
  systemctl daemon-reload
}

switch_to() {
  ln -sfn "$1" "$base/current.new"
  mv -Tf "$base/current.new" "$base/current"
}

if [[ ${1:-} == --rollback ]]; then
  [[ -L $base/previous ]] || { echo 'Não há versão anterior registrada.' >&2; exit 2; }
  target=$(readlink -f "$base/previous")
  switch_to "$target"
  echo "Sincronização voltou para $(basename "$target")"
  exit 0
fi

revision=${1:-}
[[ $revision =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Uso: deploy-sync-code.sh <commit> | --rollback' >&2; exit 2; }

if [[ ! -d $repo/.git ]]; then git clone --quiet --branch "$branch" "$repo_url" "$repo"; fi
git -C "$repo" fetch --quiet origin "$branch"
commit=$(git -C "$repo" rev-parse --verify --quiet "$revision^{commit}") ||
  { echo "Commit $revision não encontrado." >&2; exit 3; }
git -C "$repo" merge-base --is-ancestor "$commit" "origin/$branch" ||
  { echo "Commit $commit não pertence a origin/$branch." >&2; exit 3; }

release=$base/releases/$commit
install -d -m 0755 "$base/releases"
stage=$(mktemp -d "$base/releases/.stage-XXXXXX")
chmod 0755 "$stage"
trap 'rm -rf -- "$stage"' EXIT
for file in "${files[@]}"; do
  git -C "$repo" show "$commit:integrations/nextcloud_azura/$file" >"$stage/$file"
  chmod 0644 "$stage/$file"
done
"$venv_python" -m py_compile "$stage/sync.py" "$stage/refresh_player_catalog.py"
/usr/bin/python3 -m py_compile "$stage/queue_worker.py"
rm -rf -- "$stage/__pycache__"
rm -rf -- "$release"
mv -T "$stage" "$release"
trap - EXIT

# Não troca o código no meio de uma importação em andamento.
if systemctl is-active --quiet aggilli-nextcloud-sync.service; then
  echo 'Há uma sincronização em andamento. Tente novamente quando terminar.' >&2
  exit 4
fi
if [[ -L $base/current ]]; then ln -sfn "$(readlink -f "$base/current")" "$base/previous"; fi
switch_to "$release"
install_dropins

for unit in aggilli-nextcloud-sync.service aggilli-sync-queue.service; do
  systemctl show -p ExecStart --value "$unit" | grep -q "$base/current/" ||
    { echo "Falha: $unit não aponta para $base/current." >&2; exit 5; }
done
echo "Código da sincronização implantado: $commit"
echo "Em uso: $(readlink -f "$base/current")"
