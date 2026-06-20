"""thmes_orchestrator — L2 multi-step orchestration.

Inspired by agent-kernel's orchestrator pattern:
  1. PLAN  — small model (Gemma) generates step list from goal
  2. EXEC  — each step runs via ReAct or opencode delegation
  3. RETRY — failed steps retry up to N times
  4. REVIEW — optional reviewer agent audits result

Each step has: agent, action, message, status, output, retries.
Whole run persisted to ~/.thmes/data/orchestration.db.
"""
from __future__ import annotations
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


ORCH_DB = Path.home() / ".thmes" / "data" / "orchestration.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Step planning prompt (gives the LLM a few-shot example) ─────────────
PLAN_PROMPT = """You are a planner. Decompose this goal into 2-6 concrete steps.

Goal: {goal}

Available agents (pick best fit per step):
{agent_list}

Output EXACTLY a JSON object — no other text, no markdown fences:
{{
  "steps": [
    {{"agent": "AGENT", "action": "short verb phrase", "message": "what the agent should do"}},
    ...
  ]
}}

Rules:
- 2-6 steps total. Each step must produce a tangible artifact or decision.
- Pick agents whose role matches (planner for analysis, executor for code/files).
- "message" should be a complete instruction the agent can act on standalone.
- For code/file work, prefer executors: backend-dev, frontend-dev, debugger, data-engineer.
- For planning/review, prefer: analyst, architect, reviewer.

Example for "implement a Python script that lists files in a dir":
{{"steps":[
  {{"agent":"architect","action":"design","message":"Specify the script's CLI: args, output format, error handling"}},
  {{"agent":"backend-dev","action":"implement","message":"Write the Python script per the spec at /tmp/list_files.py"}},
  {{"agent":"reviewer","action":"review","message":"Read /tmp/list_files.py and flag any bugs or missing edge cases"}}
]}}
"""


class OrchestrationStore:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS orch_runs (
      id           TEXT PRIMARY KEY,
      goal         TEXT NOT NULL,
      status       TEXT NOT NULL,         -- planning|running|completed|failed|cancelled
      total_steps  INTEGER DEFAULT 0,
      completed_steps INTEGER DEFAULT 0,
      created_at   TEXT NOT NULL,
      updated_at   TEXT NOT NULL,
      finished_at  TEXT,
      metadata     TEXT
    );
    CREATE TABLE IF NOT EXISTS orch_steps (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id       TEXT NOT NULL,
      step_num     INTEGER NOT NULL,
      agent        TEXT,
      action       TEXT,
      message      TEXT,
      status       TEXT NOT NULL,         -- pending|running|done|failed|skipped
      retries      INTEGER DEFAULT 0,
      output       TEXT,
      error        TEXT,
      duration_ms  INTEGER,
      started_at   TEXT,
      finished_at  TEXT,
      FOREIGN KEY (run_id) REFERENCES orch_runs(id)
    );
    CREATE INDEX IF NOT EXISTS idx_orch_step_run ON orch_steps(run_id, step_num);
    """

    def __init__(self, db_path: Path = ORCH_DB):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("PRAGMA journal_mode=WAL;")
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

    def create_run(self, goal: str, metadata: dict | None = None) -> str:
        rid = uuid.uuid4().hex[:12]
        now = _now()
        self.conn.execute(
            "INSERT INTO orch_runs(id,goal,status,created_at,updated_at,metadata) "
            "VALUES(?,?,?,?,?,?)",
            (rid, goal, "planning", now, now,
             json.dumps(metadata) if metadata else None))
        self.conn.commit()
        return rid

    def update_run(self, rid: str, **kwargs):
        if not kwargs: return
        kwargs["updated_at"] = _now()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [rid]
        self.conn.execute(f"UPDATE orch_runs SET {fields} WHERE id=?", vals)
        self.conn.commit()

    def add_step(self, rid: str, step_num: int, agent: str, action: str, message: str):
        self.conn.execute(
            "INSERT INTO orch_steps(run_id,step_num,agent,action,message,status) "
            "VALUES(?,?,?,?,?,?)",
            (rid, step_num, agent, action, message, "pending"))
        self.conn.commit()

    def update_step(self, rid: str, step_num: int, **kwargs):
        if not kwargs: return
        fields = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [rid, step_num]
        self.conn.execute(
            f"UPDATE orch_steps SET {fields} WHERE run_id=? AND step_num=?", vals)
        self.conn.commit()

    def get_run(self, rid: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM orch_runs WHERE id=?", (rid,)).fetchone()
        if not r: return None
        steps = self.conn.execute(
            "SELECT * FROM orch_steps WHERE run_id=? ORDER BY step_num",
            (rid,)).fetchall()
        d = dict(r); d["steps"] = [dict(s) for s in steps]
        return d

    def list_runs(self, limit: int = 30) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,goal,status,total_steps,completed_steps,created_at "
            "FROM orch_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        try: self.conn.close()
        except: pass


# ── Planner ──────────────────────────────────────────────────────────────
def parse_plan(reply: str) -> list[dict]:
    """Extract steps from LLM's JSON output (tolerant)."""
    # Find first {…} block with "steps"
    dec = json.JSONDecoder()
    for i, ch in enumerate(reply):
        if ch != "{": continue
        try:
            obj, _ = dec.raw_decode(reply[i:])
            if isinstance(obj, dict) and "steps" in obj:
                return [s for s in obj["steps"]
                        if isinstance(s, dict) and "agent" in s and "message" in s][:6]
        except json.JSONDecodeError:
            continue
    # Fallback: extract any agent/message pairs from numbered list
    steps = []
    for m in re.finditer(r"(\d+)[.)]\s*(?:agent[:=]\s*)?([\w-]+)[:\s]+(.+?)(?=\d+[.)]|\Z)",
                          reply, re.DOTALL):
        steps.append({
            "agent": m.group(2),
            "action": "execute",
            "message": m.group(3).strip()[:300],
        })
    return steps[:6]


class Orchestrator:
    """Multi-step execution wrapper."""

    def __init__(self, agents: dict, generate_fn: Callable, exec_step_fn: Callable,
                 store: OrchestrationStore | None = None,
                 on_event: Callable | None = None,
                 max_retries: int = 2):
        """
        Args:
          agents:       dict of agent_name → {role, description, system, ...}
          generate_fn:  callable(prompt: str, max_tokens: int) -> str
                        Used for plan generation (small task)
          exec_step_fn: callable(agent: str, message: str) -> (output: str, ok: bool)
                        Used to execute each step
          store:        OrchestrationStore for persistence (None = ephemeral)
          on_event:     callable(event_type: str, data: dict) for streaming updates
          max_retries:  per-step retry budget
        """
        self.agents = agents
        self.generate = generate_fn
        self.exec_step = exec_step_fn
        self.store = store or OrchestrationStore()
        self.on_event = on_event or (lambda *_: None)
        self.max_retries = max_retries

    def plan(self, goal: str) -> tuple[list[dict], str]:
        """Generate step list. Returns (steps, raw_reply)."""
        agent_list = "\n".join(
            f"  - {n} ({a.get('role','?')}): {a.get('description','')[:80]}"
            for n, a in self.agents.items())
        prompt = PLAN_PROMPT.format(goal=goal, agent_list=agent_list)
        self.on_event("plan_start", {"goal": goal})
        reply = self.generate(prompt, max_tokens=600)
        steps = parse_plan(reply)
        self.on_event("plan_done", {"steps": steps, "raw_len": len(reply)})
        return steps, reply

    def run(self, goal: str, with_review: bool = False) -> dict:
        """Execute end-to-end: plan → execute → optional review.
        Returns the full run record.
        """
        rid = self.store.create_run(goal)
        self.on_event("run_start", {"run_id": rid, "goal": goal})

        # ── Plan phase ─────────────────────────────────────────────────
        try:
            steps, raw = self.plan(goal)
        except Exception as e:
            self.store.update_run(rid, status="failed",
                                  metadata=json.dumps({"plan_error": str(e)}))
            self.on_event("run_failed", {"run_id": rid, "phase": "plan", "error": str(e)})
            return self.store.get_run(rid)

        if not steps:
            self.store.update_run(rid, status="failed",
                                  metadata=json.dumps({"reason": "empty plan"}))
            self.on_event("run_failed", {"run_id": rid, "phase": "plan",
                                          "error": "no steps parsed"})
            return self.store.get_run(rid)

        # Persist steps
        for i, s in enumerate(steps):
            self.store.add_step(rid, i + 1, s["agent"], s.get("action", "execute"),
                                s["message"])
        self.store.update_run(rid, status="running", total_steps=len(steps))
        self.on_event("steps_planned", {"run_id": rid, "count": len(steps), "steps": steps})

        # ── Execute phase ──────────────────────────────────────────────
        completed = 0
        failed_steps: list[int] = []
        outputs: list[str] = []
        for i, s in enumerate(steps, start=1):
            agent_name = s["agent"] if s["agent"] in self.agents else "general"
            msg = s["message"]
            self.on_event("step_start", {"run_id": rid, "step": i, "total": len(steps),
                                          "agent": agent_name, "message": msg})
            start = time.time()
            output, ok, retries = "", False, 0
            err = None
            for attempt in range(self.max_retries + 1):
                t0 = time.time()
                self.store.update_step(rid, i, status="running", started_at=_now())
                try:
                    output, ok = self.exec_step(agent_name, msg)
                except Exception as e:
                    output = ""; ok = False; err = str(e)
                if ok: break
                retries = attempt + 1
                self.on_event("step_retry", {"run_id": rid, "step": i,
                                              "attempt": retries})
            duration = int((time.time() - start) * 1000)
            self.store.update_step(
                rid, i,
                status="done" if ok else "failed",
                retries=retries,
                output=output[:5000],
                error=err,
                duration_ms=duration,
                finished_at=_now(),
            )
            if ok:
                completed += 1
                outputs.append(f"[step {i} | {agent_name}]\n{output[:1500]}")
                self.on_event("step_done", {"run_id": rid, "step": i,
                                             "duration_ms": duration,
                                             "output_preview": output[:200]})
            else:
                failed_steps.append(i)
                self.on_event("step_failed", {"run_id": rid, "step": i,
                                                "retries": retries, "error": err or "exec failed"})
                # Stop on hard failure; alternative: continue best-effort
                break
            self.store.update_run(rid, completed_steps=completed)

        # ── Review phase (optional) ────────────────────────────────────
        if with_review and not failed_steps and "reviewer" in self.agents:
            review_msg = ("Review the outputs of the orchestration. "
                          "Flag any contradictions, missing pieces, or quality issues.\n\n"
                          + "\n\n".join(outputs))
            self.on_event("review_start", {"run_id": rid})
            try:
                review_out, ok = self.exec_step("reviewer", review_msg)
                self.store.update_run(rid, metadata=json.dumps({
                    "review": review_out[:3000], "review_ok": ok,
                }))
                self.on_event("review_done", {"run_id": rid, "review": review_out[:200]})
            except Exception as e:
                self.on_event("review_failed", {"run_id": rid, "error": str(e)})

        # ── Final status ───────────────────────────────────────────────
        final = "completed" if not failed_steps else "failed"
        self.store.update_run(rid, status=final, finished_at=_now())
        self.on_event("run_finished", {"run_id": rid, "status": final,
                                        "completed": completed, "total": len(steps)})
        return self.store.get_run(rid)
