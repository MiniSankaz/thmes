"""thmes_registry — Hot-swappable runtime config (model, defaults, flags).

Cross-process key-value store using SQLite WAL — every process reads fresh
value on each call. No restart needed when admin changes the active model.

Use cases:
  • thmes-pro `/model qwen-vl` → updates registry → next goal in thmes-daemon
    picks up new model without restart
  • A/B test models across sessions
  • Per-role model preference (planner=gemma, executor=qwen-vl)
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_DB = Path.home() / ".thmes" / "data" / "registry.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Registry:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS runtime_config (
      key        TEXT PRIMARY KEY,
      value      TEXT NOT NULL,         -- JSON
      updated_at TEXT NOT NULL,
      updated_by TEXT
    );
    CREATE TABLE IF NOT EXISTS subscriptions (
      key         TEXT NOT NULL,
      subscriber  TEXT NOT NULL,        -- e.g. "agent" | "daemon" | "tui"
      created_at  TEXT NOT NULL,
      PRIMARY KEY (key, subscriber)
    );
    """

    def __init__(self, db_path: Path = REGISTRY_DB):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False,
                                     isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=2000;")
        self.conn.executescript(self.SCHEMA)
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 1.0  # 1 sec cache (still hot-swap effectively)

    def set(self, key: str, value: Any, who: str = "") -> None:
        s = json.dumps(value)
        now = _now()
        self.conn.execute(
            "INSERT OR REPLACE INTO runtime_config(key,value,updated_at,updated_by) "
            "VALUES(?,?,?,?)",
            (key, s, now, who or os.environ.get("USER", "?")))
        self._cache.pop(key, None)  # invalidate

    def get(self, key: str, default: Any = None) -> Any:
        """Fresh read from DB (with 1s cache for performance)."""
        now = time.time()
        if key in self._cache:
            ts, val = self._cache[key]
            if now - ts < self._cache_ttl:
                return val
        row = self.conn.execute(
            "SELECT value FROM runtime_config WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        try:
            val = json.loads(row["value"])
        except json.JSONDecodeError:
            val = row["value"]
        self._cache[key] = (now, val)
        return val

    def delete(self, key: str) -> bool:
        c = self.conn.execute("DELETE FROM runtime_config WHERE key=?", (key,))
        self._cache.pop(key, None)
        return c.rowcount > 0

    def items(self) -> dict[str, Any]:
        out = {}
        for r in self.conn.execute("SELECT key, value FROM runtime_config").fetchall():
            try: out[r["key"]] = json.loads(r["value"])
            except json.JSONDecodeError: out[r["key"]] = r["value"]
        return out

    def subscribe(self, key: str, subscriber: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO subscriptions(key,subscriber,created_at) VALUES(?,?,?)",
            (key, subscriber, _now()))

    def subscribers(self, key: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT subscriber FROM subscriptions WHERE key=?", (key,)).fetchall()
        return [r["subscriber"] for r in rows]

    # ── Convenience accessors ────────────────────────────────────────────
    def current_model(self, default: str = "gemma") -> str:
        return self.get("model.active", default)

    def set_current_model(self, name: str, who: str = "tui"):
        self.set("model.active", name, who=who)

    def role_model(self, role: str, default: str | None = None) -> str | None:
        """Per-role default. E.g., role='executor' → 'qwen-vl'."""
        return self.get(f"model.role.{role}", default)

    def set_role_model(self, role: str, name: str, who: str = ""):
        self.set(f"model.role.{role}", name, who=who)

    def close(self):
        try: self.conn.close()
        except: pass


# Singleton instance
_REGISTRY: Registry | None = None

def get_registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = Registry()
    return _REGISTRY
