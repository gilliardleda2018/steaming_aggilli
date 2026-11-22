"""Isolated SQLite identity and entitlement store for commercial staging.

No production wiring, no payment processor, no media delivery.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or len(password) < 12 or len(password) > 256:
        raise ValueError("Password length must be 12..256")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return "pbkdf2_sha256$600000$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != 600_000:
            return False
        expected = bytes.fromhex(digest)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError, AttributeError):
        return False


class ListenerStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("Symlink database refused")
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS listeners(
          id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY, listener_id TEXT NOT NULL,
          expires_at TEXT NOT NULL, FOREIGN KEY(listener_id) REFERENCES listeners(id)
        );
        CREATE TABLE IF NOT EXISTS subscriptions(
          listener_id TEXT PRIMARY KEY, plan TEXT NOT NULL,
          status TEXT NOT NULL, access_until TEXT NOT NULL,
          FOREIGN KEY(listener_id) REFERENCES listeners(id)
        );
        """)
        os.chmod(self.path, 0o600)
        return db

    def register(self, email: str, password: str):
        email = email.strip().lower()
        if not 3 <= len(email) <= 254 or email.count("@") != 1 or any(c.isspace() for c in email):
            raise ValueError("Invalid email")
        encoded = hash_password(password)
        listener_id = secrets.token_hex(16)
        with self.connect() as db:
            db.execute("INSERT INTO listeners(id,email,password_hash,created_at) VALUES(?,?,?,?)",
                       (listener_id, email, encoded, utcnow().isoformat()))
        return listener_id

    def login(self, email: str, password: str):
        email = email.strip().lower()
        with self.connect() as db:
            row = db.execute("SELECT * FROM listeners WHERE email=?", (email,)).fetchone()
            if not row or row["status"] != "active" or not verify_password(password, row["password_hash"]):
                return None
            token = secrets.token_urlsafe(32)
            expiry = utcnow() + timedelta(hours=12)
            db.execute("INSERT INTO sessions(token_hash,listener_id,expires_at) VALUES(?,?,?)",
                       (hashlib.sha256(token.encode()).hexdigest(), row["id"], expiry.isoformat()))
            return token

    def authenticate(self, token: str):
        if not isinstance(token, str) or len(token) > 256 or len(token) < 32:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        return self.authenticate_session_hash(digest)

    def authenticate_session_hash(self, digest: str):
        with self.connect() as db:
            row = db.execute("""SELECT l.id,l.status,s.expires_at FROM sessions s
                JOIN listeners l ON l.id=s.listener_id WHERE s.token_hash=?""", (digest,)).fetchone()
            if not row or row["status"] != "active":
                return None
            if datetime.fromisoformat(row["expires_at"]) <= utcnow():
                db.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
                return None
            return {"id": row["id"], "status": row["status"]}

    def logout(self, token: str):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def subscription(self, listener_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM subscriptions WHERE listener_id=?", (listener_id,)).fetchone()
            return dict(row) if row else None

    def set_subscription(self, listener_id: str, plan: str, status: str, access_until: str):
        if plan not in {"free", "premium", "family"} or status not in {"active", "trialing", "past_due", "canceled"}:
            raise ValueError("Invalid subscription")
        expiry = datetime.fromisoformat(access_until.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            raise ValueError("Timezone required")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM listeners WHERE id=?", (listener_id,)).fetchone():
                raise KeyError(listener_id)
            db.execute("""INSERT INTO subscriptions(listener_id,plan,status,access_until)
                VALUES(?,?,?,?) ON CONFLICT(listener_id) DO UPDATE SET
                plan=excluded.plan,status=excluded.status,access_until=excluded.access_until""",
                (listener_id, plan, status, expiry.isoformat()))
