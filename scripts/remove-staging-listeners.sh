#!/usr/bin/env bash
# Remove contas de ouvinte de homologação (e-mails @aggilli.test) da API comercial,
# com suas sessões, assinaturas e limites. Faz cópia do banco antes de apagar.
# Rode como root:
#   bash scripts/remove-staging-listeners.sh dj-homologacao@aggilli.test dj-homologacao-2@aggilli.test
set -Eeuo pipefail

readonly db=/var/lib/aggilli-music-commercial/listeners.db
readonly backups=/var/backups/aggilli-music

[[ $EUID -eq 0 ]] || { echo "Rode como root (su - -c '...')." >&2; exit 1; }
(( $# > 0 )) || { echo "Informe ao menos um e-mail @aggilli.test." >&2; exit 1; }
for email in "$@"; do
  [[ $email =~ ^[A-Za-z0-9._+-]+@aggilli\.test$ ]] \
    || { echo "Recusado: só contas de homologação @aggilli.test ($email)." >&2; exit 1; }
done
[[ -f $db && ! -L $db ]] || { echo "Banco não encontrado: $db" >&2; exit 1; }

install -d -m 0700 "$backups"
backup="$backups/listeners-$(date +%Y%m%d-%H%M%S).db"

python3 -I - "$db" "$backup" "$@" <<'PY'
import os, sqlite3, sys

db_path, backup_path, emails = sys.argv[1], sys.argv[2], sys.argv[3:]
db = sqlite3.connect(db_path, timeout=10)
backup = sqlite3.connect(backup_path)
db.backup(backup)
backup.close()
os.chmod(backup_path, 0o600)
print("Cópia do banco:", backup_path)

db.execute("PRAGMA foreign_keys=ON")
with db:
    for email in emails:
        row = db.execute("SELECT id FROM listeners WHERE email = ?", (email.lower(),)).fetchone()
        if not row:
            print(f"{email}: não existe (nada a fazer)")
            continue
        listener_id = row[0]
        sessions = db.execute("DELETE FROM sessions WHERE listener_id = ?", (listener_id,)).rowcount
        db.execute("DELETE FROM subscriptions WHERE listener_id = ?", (listener_id,))
        db.execute("DELETE FROM listener_rate_limits WHERE listener_id = ?", (listener_id,))
        db.execute("DELETE FROM listeners WHERE id = ?", (listener_id,))
        print(f"{email}: removida ({sessions} sessão(ões) encerrada(s))")
left = db.execute("SELECT COUNT(*) FROM listeners").fetchone()[0]
print("Contas restantes:", left)
PY
