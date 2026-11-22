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
            report("success" if result.returncode == 0 else "failed",
                   "Importação concluída" if result.returncode == 0 else "Falha na importação; consulte journalctl")
        except (OSError, subprocess.TimeoutExpired):
            report("failed", "Não foi possível concluir o serviço")


if __name__ == "__main__":
    main()
