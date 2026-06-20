"""thmes_goals — L3 Autonomous goal queue.

Persistent queue of goals processed by a background worker daemon (or in-process
worker thread). Each goal becomes an orchestration run when picked up.

Goal lifecycle:
  queued → running → (completed | failed | cancelled)

Features:
  • Priority (critical/high/normal/low) with FIFO within tier
  • Schedule: immediate, at specific time, or cron pattern (one-shot first only)
  • Retries: per-goal retry budget
  • Lock: only one process at a time picks (atomic UPDATE … RETURNING)
"""
from __future__ import annotations
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


GOALS_DB = Path.home() / ".thmes" / "data" / "goals.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class GoalQueue:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS goals (
      id           TEXT PRIMARY KEY,
      goal         TEXT NOT NULL,
      priority     TEXT NOT NULL DEFAULT 'normal',
      status       TEXT NOT NULL DEFAULT 'queued',  -- queued|running|completed|failed|cancelled
      with_review  INTEGER DEFAULT 0,
      run_id       TEXT,                            -- orchestration run id, if started
      worker_pid   INTEGER,                          -- pid of process running it
      schedule_at  TEXT,                             -- ISO timestamp, NULL = immediate
      retries      INTEGER DEFAULT 0,
      max_retries  INTEGER DEFAULT 2,
      created_at   TEXT NOT NULL,
      updated_at   TEXT NOT NULL,
      started_at   TEXT,
      finished_at  TEXT,
      result       TEXT,
      error        TEXT,
      metadata     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_goals_status   ON goals(status);
    CREATE INDEX IF NOT EXISTS idx_goals_schedule ON goals(schedule_at);
    CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority);
    """

    def __init__(self, db_path: Path = GOALS_DB):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False,
                                     isolation_level=None)  # autocommit
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;")
        self.conn.executescript(self.SCHEMA)

    # ── Add/Cancel ───────────────────────────────────────────────────────
    def add(self, goal: str, priority: str = "normal",
            schedule_at: str | None = None, with_review: bool = False,
            max_retries: int = 2, metadata: dict | None = None) -> str:
        gid = uuid.uuid4().hex[:12]
        if priority not in PRIORITY_RANK: priority = "normal"
        now = _now()
        self.conn.execute(
            "INSERT INTO goals(id,goal,priority,status,with_review,schedule_at,"
            "max_retries,created_at,updated_at,metadata) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (gid, goal, priority, "queued", 1 if with_review else 0,
             schedule_at, max_retries, now, now,
             json.dumps(metadata) if metadata else None))
        return gid

    def cancel(self, gid: str) -> bool:
        c = self.conn.execute(
            "UPDATE goals SET status='cancelled', updated_at=?, finished_at=? "
            "WHERE id=? AND status IN ('queued','running')",
            (_now(), _now(), gid))
        return c.rowcount > 0

    # ── Worker primitives ───────────────────────────────────────────────
    def claim_next(self, worker_pid: int) -> dict | None:
        """Atomically claim the next runnable goal. Returns the goal row or None."""
        now = _now()
        # SQLite doesn't have UPDATE … RETURNING in all versions; use 2-step with transaction
        cur = self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT * FROM goals WHERE status='queued' "
                "AND (schedule_at IS NULL OR schedule_at <= ?) "
                "ORDER BY CASE priority "
                "  WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                "  WHEN 'normal' THEN 2 ELSE 3 END, created_at "
                "LIMIT 1", (now,)).fetchone()
            if not row:
                self.conn.execute("ROLLBACK")
                return None
            self.conn.execute(
                "UPDATE goals SET status='running', worker_pid=?, started_at=?, updated_at=? "
                "WHERE id=? AND status='queued'",
                (worker_pid, now, now, row["id"]))
            self.conn.execute("COMMIT")
            return dict(row)
        except sqlite3.Error:
            self.conn.execute("ROLLBACK")
            return None

    def mark_done(self, gid: str, status: str, run_id: str | None = None,
                  result: str | None = None, error: str | None = None):
        now = _now()
        self.conn.execute(
            "UPDATE goals SET status=?, run_id=?, result=?, error=?, "
            "updated_at=?, finished_at=? WHERE id=?",
            (status, run_id, (result or "")[:5000], (error or "")[:2000],
             now, now, gid))

    def maybe_retry(self, gid: str, error: str) -> bool:
        """If retries < max_retries, requeue. Otherwise mark failed. Returns True if requeued."""
        row = self.conn.execute(
            "SELECT retries, max_retries FROM goals WHERE id=?", (gid,)).fetchone()
        if not row: return False
        if row["retries"] < row["max_retries"]:
            self.conn.execute(
                "UPDATE goals SET status='queued', retries=retries+1, "
                "worker_pid=NULL, error=?, updated_at=? WHERE id=?",
                (error[:1000], _now(), gid))
            return True
        self.mark_done(gid, "failed", error=error)
        return False

    # ── Inspection ──────────────────────────────────────────────────────
    def get(self, gid: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM goals WHERE id=?", (gid,)).fetchone()
        return dict(r) if r else None

    def list(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT id,goal,priority,status,retries,run_id,created_at,finished_at "
                "FROM goals WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id,goal,priority,status,retries,run_id,created_at,finished_at "
                "FROM goals ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as n FROM goals GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    def close(self):
        try: self.conn.close()
        except: pass


# ── Background worker ───────────────────────────────────────────────────
class GoalWorker:
    """Polls the queue and processes goals using an Orchestrator.

    Run inside the thmes-pro app via threading, or standalone via thmes-daemon.
    """
    def __init__(self, queue: GoalQueue, orchestrator_factory, poll_interval: float = 3.0,
                 on_event=None):
        """
        Args:
          queue:                GoalQueue instance
          orchestrator_factory: callable() → Orchestrator. Called per goal so model state
                                stays per-invocation.
          poll_interval:        seconds between queue polls when idle
          on_event:             callable(evt: str, data: dict)
        """
        self.queue = queue
        self.orch_factory = orchestrator_factory
        self.poll_interval = poll_interval
        self.on_event = on_event or (lambda *_: None)
        self._stop = False
        self.pid = os.getpid()

    def stop(self):
        self._stop = True

    def run_one(self) -> bool:
        """Process exactly one goal. Returns True if a goal was claimed, False if idle."""
        claimed = self.queue.claim_next(self.pid)
        if not claimed: return False
        gid = claimed["id"]
        self.on_event("goal_start", {"id": gid, "goal": claimed["goal"],
                                       "priority": claimed["priority"]})
        try:
            orch = self.orch_factory()
            result = orch.run(claimed["goal"], with_review=bool(claimed["with_review"]))
            status = result.get("status", "failed")
            run_id = result.get("id")
            if status == "completed":
                self.queue.mark_done(gid, "completed", run_id=run_id,
                                      result=f"{result['completed_steps']}/{result['total_steps']} steps")
                self.on_event("goal_done", {"id": gid, "run_id": run_id})
            else:
                # Failed → try retry
                if self.queue.maybe_retry(gid, error=f"orch failed: {status}"):
                    self.on_event("goal_retry", {"id": gid})
                else:
                    self.on_event("goal_failed", {"id": gid, "run_id": run_id})
        except Exception as e:
            if self.queue.maybe_retry(gid, error=str(e)):
                self.on_event("goal_retry", {"id": gid, "error": str(e)})
            else:
                self.on_event("goal_failed", {"id": gid, "error": str(e)})
        return True

    def loop(self):
        """Block-loop. Use in a thread or daemon process."""
        import time as _time
        self.on_event("worker_start", {"pid": self.pid})
        while not self._stop:
            try:
                processed = self.run_one()
                if not processed:
                    _time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.on_event("worker_error", {"error": str(e)})
                _time.sleep(self.poll_interval)
        self.on_event("worker_stop", {"pid": self.pid})
