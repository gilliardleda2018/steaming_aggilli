#!/usr/bin/env python3
"""Consume one authenticated queue request, without executing its contents."""
import datetime
import fcntl
import json
import os
import subprocess
from pathlib import Path

BASE = Path("/var/lib/aggilli-music")
QUEUE = BASE / "sync-requests" / "pending"
STATUS = BASE / "sync-status.json"
LOCK = BASE / "sync-worker.lock"
UNIT = "aggilli-nextcloud-sync.service"
CATALOG_REFRESH = "/home/gilliard/projetos/steaming_aggilli/integrations/nextcloud_azura/refresh_player_catalog.py"
PYTHON = "/opt/aggilli-nextcloud-sync-venv/bin/python"


def report(state, message):
    data = {"state": state, "message": message,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    temp = STATUS.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False))
    os.chmod(temp, 0o644)
    os.replace(temp, STATUS)


def main():
    with LOCK.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if not QUEUE.exists():
            return
        active = subprocess.run(["/usr/bin/systemctl", "is-active", "--quiet", UNIT]).returncode == 0
        if active:
            report("running", "Sincronização anterior ainda está em andamento")
            return
        # The request content is intentionally ignored; fixed service only.
        QUEUE.unlink()
        report("running", "Importação iniciada")
        try:
            result = subprocess.run(
                ["/usr/bin/systemctl", "start", "--wait", UNIT],
                timeout=6 * 3600 + 60, capture_output=True, text=True,
            )
            if result.returncode != 0:
                report("failed", "Falha na importação; consulte journalctl")
                return
            refresh = subprocess.run(
                [PYTHON, CATALOG_REFRESH],
                timeout=90, capture_output=True, text=True,
            )
            if refresh.returncode == 0:
                report("success", "Importação concluída e catálogo do Winamp atualizado")
            else:
                report("failed", "Importação concluída, mas atualização do catálogo falhou: "
                       + (refresh.stderr.strip() or refresh.stdout.strip())[-350:])
        except (OSError, subprocess.TimeoutExpired):
            report("failed", "Não foi possível concluir o serviço")


if __name__ == "__main__":
    main()
