"""Durable SQLite queue with expiring, fenced worker claims.

Every operation uses a fresh connection. BEGIN IMMEDIATE makes queue admission and
claim selection atomic even when several API processes share the same database.
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any, Iterator


class QueueFull(Exception):
    pass


class ReviewUnavailable(Exception):
    pass


class ReviewNotReady(Exception):
    pass


class JobStore:
    def __init__(self, data_dir: Path, capacity: int = 4) -> None:
        self.data_dir = data_dir.resolve()
        self.media_dir = self.data_dir / "media"
        self.media_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db_path = self.data_dir / "jobs.sqlite3"
        self.capacity = capacity
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('processing','done','failed')),
                    media_name TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    deadline_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    token_hash TEXT,
                    token_expires_at REAL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    stage TEXT NOT NULL DEFAULT 'queued',
                    claim_token TEXT,
                    lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    finished_at REAL
                );
                CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(status,created_at);
                CREATE INDEX IF NOT EXISTS jobs_expiry ON jobs(expires_at);
                CREATE TABLE IF NOT EXISTS human_reviews (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                    decision TEXT NOT NULL CHECK(decision IN ('violation','no_violation','needs_review')),
                    notes TEXT NOT NULL CHECK(length(notes)<=4000),
                    event_index INTEGER CHECK(event_index IS NULL OR event_index>=0),
                    updated_at REAL NOT NULL
                );
            """)
        # POSIX deployments use owner-only permissions; Windows uses the host's ACL.
        if os.name != "nt":
            self.data_dir.chmod(0o700)
            self.db_path.chmod(0o600)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, job_id: str, media_name: str, size: int, digest: str,
               deadline_seconds: float, retention_seconds: float,
               token: str | None = None, token_ttl: float = 7200,
               now: float | None = None, admitted_at: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        created_at = now if admitted_at is None else admitted_at
        if created_at + deadline_seconds <= now:
            raise TimeoutError("Upload consumed the analysis deadline")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("""UPDATE jobs SET status='failed',stage='failed',
                    error_code='deadline_exceeded',error_message='Analysis exceeded the five-minute deadline.',
                    finished_at=?,claim_token=NULL,lease_until=NULL
                    WHERE status='processing' AND deadline_at<=?""", (now, now))
                count = db.execute("SELECT COUNT(*) FROM jobs WHERE status='processing'").fetchone()[0]
                if count >= self.capacity:
                    raise QueueFull()
                db.execute("""INSERT INTO jobs
                    (id,status,media_name,size_bytes,sha256,created_at,deadline_at,expires_at,token_hash,token_expires_at)
                    VALUES (?,'processing',?,?,?,?,?,?,?,?)""",
                    (job_id, media_name, size, digest, created_at, created_at + deadline_seconds,
                     now + retention_seconds, self.token_hash(token) if token else None,
                     now + token_ttl if token else None))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return self.get(job_id)  # type: ignore[return-value]

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def authorize(self, job: dict[str, Any], token: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return bool(job["token_hash"] and job["token_expires_at"] > now and
                    secrets.compare_digest(job["token_hash"], self.token_hash(token)))

    def get_review(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute("SELECT decision,notes,event_index,updated_at FROM human_reviews WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def save_review(self, job_id: str, decision: str, notes: str, event_index: int | None = None,
                    now: float | None = None) -> dict[str, Any]:
        """Persist a human judgment separately; never update the model result."""
        now = time.time() if now is None else now
        if decision not in {"violation", "no_violation", "needs_review"} or not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError("Invalid human review")
        if event_index is not None and (type(event_index) is not int or event_index < 0):
            raise ValueError("Invalid event index")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                job = db.execute("SELECT status,expires_at,result_json FROM jobs WHERE id=?", (job_id,)).fetchone()
                if job is None or job["expires_at"] <= now:
                    raise ReviewUnavailable()
                if job["status"] != "done":
                    raise ReviewNotReady()
                if event_index is not None and event_index >= len(json.loads(job["result_json"])["violations"]):
                    raise ValueError("Event index is outside this model result")
                db.execute("""INSERT INTO human_reviews(job_id,decision,notes,event_index,updated_at)
                    VALUES (?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET
                    decision=excluded.decision,notes=excluded.notes,event_index=excluded.event_index,
                    updated_at=excluded.updated_at""", (job_id, decision, notes, event_index, now))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return {"decision": decision, "notes": notes, "event_index": event_index, "updated_at": now}

    def claim(self, lease_seconds: float, now: float | None = None) -> dict[str, Any] | None:
        now = time.time() if now is None else now
        token = secrets.token_hex(24)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("""SELECT id FROM jobs WHERE status='processing'
                    AND deadline_at>? AND (claim_token IS NULL OR lease_until<=?)
                    ORDER BY created_at LIMIT 1""", (now, now)).fetchone()
                if row is None:
                    db.execute("COMMIT")
                    return None
                db.execute("""UPDATE jobs SET claim_token=?,lease_until=?,attempts=attempts+1,
                    stage='decoding',progress=1 WHERE id=?""", (token, now + lease_seconds, row["id"]))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return self.get(row["id"])

    def heartbeat(self, job_id: str, token: str, lease_seconds: float, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self.connection() as db:
            db.execute("""UPDATE jobs SET lease_until=? WHERE id=? AND claim_token=?
                AND status='processing' AND deadline_at>? AND lease_until>?""", (now + lease_seconds, job_id, token, now, now))

    def progress(self, job_id: str, token: str, percent: int, stage: str) -> None:
        now = time.time()
        with self.connection() as db:
            db.execute("""UPDATE jobs SET progress=MAX(progress,?),stage=?
                WHERE id=? AND claim_token=? AND status='processing' AND deadline_at>? AND lease_until>?""",
                (min(99, max(1, int(percent))), str(stage)[:120], job_id, token, now, now))

    def finish(self, job_id: str, token: str, result: dict[str, Any], now: float | None = None) -> bool:
        now = time.time() if now is None else now
        serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
        with self.connection() as db:
            changed = db.execute("""UPDATE jobs SET status='done',progress=100,stage='complete',
                result_json=?,finished_at=?,claim_token=NULL,lease_until=NULL
                WHERE id=? AND claim_token=? AND status='processing' AND deadline_at>? AND lease_until>?""",
                (serialized, now, job_id, token, now, now)).rowcount
        return bool(changed)

    def fail(self, job_id: str, token: str, code: str, message: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self.connection() as db:
            changed = db.execute("""UPDATE jobs SET status='failed',stage='failed',error_code=?,
                error_message=?,finished_at=?,claim_token=NULL,lease_until=NULL
                WHERE id=? AND claim_token=? AND status='processing' AND deadline_at>? AND lease_until>?""",
                (code, message, now, job_id, token, now, now)).rowcount
        return bool(changed)

    def expire_deadlines(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.connection() as db:
            return db.execute("""UPDATE jobs SET status='failed',stage='failed',
                error_code='deadline_exceeded',error_message='Analysis exceeded the five-minute deadline.',
                finished_at=?,claim_token=NULL,lease_until=NULL
                WHERE status='processing' AND deadline_at<=?""", (now, now)).rowcount

    def cleanup(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT id,media_name FROM jobs WHERE expires_at<? AND status!='processing'", (now,)).fetchall()
            db.executemany("DELETE FROM jobs WHERE id=?", [(r["id"],) for r in rows])
            db.execute("COMMIT")
        for row in rows:
            try:
                self.media_path(row["media_name"]).unlink(missing_ok=True)
            except OSError:
                # Locked files are retried by orphan cleanup on the next pass.
                pass
        with self.connection() as db:
            referenced = {row[0] for row in db.execute("SELECT media_name FROM jobs")}
        # Remove interrupted uploads/admissions after a generous grace period.
        for path in self.media_dir.glob("*.part"):
            try:
                if path.stat().st_mtime < now - 3600:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
        for path in self.media_dir.glob("*.mov"):
            try:
                if path.name not in referenced and path.stat().st_mtime < now - 3600:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
        return len(rows)

    def media_path(self, media_name: str) -> Path:
        path = (self.media_dir / media_name).resolve()
        if path.parent != self.media_dir.resolve():
            raise ValueError("Invalid stored media path")
        return path
