"""thmes_memory — Multi-tier memory for thmes.

Tiers:
  L1 working   — current turn (in-memory, not stored)
  L2 episodic  — session-scoped (TTL: archive when session ends)
  L3 semantic  — permanent (cross-session, embedding-based recall)
  L4 reference — pinned facts (permanent, exact key)

Storage:
  ~/.thmes/data/memory.db
    memory       — main table (id, tier, scope, key, content, agent, embedding, ttl)
    memory_fts   — FTS5 virtual table for full-text search
    embeddings   — BLOB-stored float32 vectors (cosine search in Python)
"""
from __future__ import annotations
import json
import sqlite3
import struct
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MEMORY_DB = Path.home() / ".thmes" / "data" / "memory.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EmbeddingEngine:
    """Lazy-loaded MLX embedding model. Falls back to None if load fails."""
    def __init__(self, model_repo: str = "mlx-community/nomicai-modernbert-embed-base-4bit"):
        self.model_repo = model_repo
        self.model = None
        self.tokenizer = None
        self.dim: Optional[int] = None

    def load(self) -> bool:
        if self.model is not None: return True
        try:
            from mlx_embeddings import load
            self.model, self.tokenizer = load(self.model_repo)
            # Probe dimension
            v = self.embed("dimension probe")
            self.dim = len(v) if v is not None else None
            return self.dim is not None
        except Exception as e:
            print(f"[memory] embedding load failed: {e}")
            return False

    def embed(self, text: str) -> Optional[list[float]]:
        if self.model is None and not self.load():
            return None
        try:
            import mlx.core as mx
            # mlx_embeddings models return last_hidden_state — mean-pool over tokens
            inputs = self.tokenizer.encode(text, return_tensors="mlx")
            out = self.model(inputs)
            # Some models return dict, some return object
            if hasattr(out, "text_embeds"):
                emb = out.text_embeds
            elif hasattr(out, "last_hidden_state"):
                emb = out.last_hidden_state.mean(axis=1)
            elif isinstance(out, dict) and "text_embeds" in out:
                emb = out["text_embeds"]
            else:
                emb = out
            if emb.ndim > 1: emb = emb[0]
            # Normalize
            norm = float(mx.linalg.norm(emb).item())
            if norm > 0: emb = emb / norm
            return [float(x) for x in emb.tolist()]
        except Exception as e:
            print(f"[memory] embed failed: {e}")
            return None


def _f32_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _f32_load(b: bytes) -> list[float]:
    n = len(b) // 4
    return list(struct.unpack(f"{n}f", b))


def _cosine(a: list[float], b: list[float]) -> float:
    """Both vectors should already be unit-normalized → dot product = cosine."""
    return sum(x * y for x, y in zip(a, b))


class MemoryService:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS memory (
      id          TEXT PRIMARY KEY,
      tier        TEXT NOT NULL,
      scope       TEXT NOT NULL,        -- e.g. session_id, "global", agent name
      key         TEXT NOT NULL,        -- short label
      content     TEXT NOT NULL,
      agent       TEXT,
      embedding   BLOB,                 -- float32 packed, optional
      tags        TEXT,                 -- comma-separated
      hit_count   INTEGER DEFAULT 0,
      created_at  TEXT NOT NULL,
      last_used   TEXT,
      expires_at  TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_memory_tier  ON memory(tier);
    CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(scope);
    CREATE INDEX IF NOT EXISTS idx_memory_key   ON memory(key);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_uniq ON memory(scope, key);

    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
      content, key, tags,
      content='memory', content_rowid='rowid'
    );
    """

    def __init__(self, db_path: Path = MEMORY_DB, embed_engine: EmbeddingEngine | None = None):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("PRAGMA journal_mode=WAL;")
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()
        self.embed = embed_engine

    # ── Store ────────────────────────────────────────────────────────────
    def store(self, tier: str, scope: str, key: str, content: str,
              agent: str | None = None, tags: str = "",
              ttl_seconds: int | None = None,
              embed: bool = False) -> str:
        mid = uuid.uuid4().hex[:12]
        now = _now_iso()
        expires = None
        if ttl_seconds:
            from datetime import timedelta
            expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                       ).isoformat(timespec="seconds")
        vec_bytes = None
        if embed and self.embed:
            v = self.embed.embed(content)
            if v: vec_bytes = _f32_bytes(v)
        try:
            self.conn.execute(
                "INSERT INTO memory(id,tier,scope,key,content,agent,embedding,tags,created_at,expires_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (mid, tier, scope, key, content, agent, vec_bytes, tags, now, expires))
        except sqlite3.IntegrityError:
            # Upsert on (scope, key)
            self.conn.execute(
                "UPDATE memory SET content=?, agent=?, embedding=?, tags=?, "
                "expires_at=?, hit_count=hit_count+1, last_used=? WHERE scope=? AND key=?",
                (content, agent, vec_bytes, tags, expires, now, scope, key))
            row = self.conn.execute(
                "SELECT id FROM memory WHERE scope=? AND key=?",
                (scope, key)).fetchone()
            mid = row["id"] if row else mid
        # Update FTS
        self.conn.execute(
            "INSERT OR REPLACE INTO memory_fts(rowid, content, key, tags) "
            "SELECT rowid, content, key, tags FROM memory WHERE id=?",
            (mid,))
        self.conn.commit()
        return mid

    # ── Recall ──────────────────────────────────────────────────────────
    def recall_by_key(self, scope: str, key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM memory WHERE scope=? AND key=?", (scope, key)).fetchone()
        if row:
            self._bump_hit(row["id"])
            return dict(row)
        return None

    def recall_fts(self, query: str, tier: str | None = None,
                   scope: str | None = None, limit: int = 5) -> list[dict]:
        # FTS5 query — sanitize special chars
        safe_q = query.replace('"', '').strip()
        if not safe_q: return []
        # Use prefix-match for each word
        terms = " OR ".join(f'"{w}"' for w in safe_q.split() if len(w) > 1)
        if not terms: return []
        q = ("SELECT m.* FROM memory_fts f JOIN memory m ON m.rowid = f.rowid "
             "WHERE memory_fts MATCH ?")
        params: list = [terms]
        if tier:  q += " AND m.tier=?";  params.append(tier)
        if scope: q += " AND m.scope=?"; params.append(scope)
        q += " ORDER BY rank LIMIT ?"
        params.append(limit)
        try:
            rows = self.conn.execute(q, params).fetchall()
            for r in rows: self._bump_hit(r["id"])
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def recall_semantic(self, query: str, tier: str = "L3",
                        scope: str | None = None, top_k: int = 5,
                        min_sim: float = 0.5) -> list[dict]:
        """Embedding cosine search. Falls back to FTS if no embeddings stored."""
        if not self.embed: return self.recall_fts(query, tier=tier, scope=scope, limit=top_k)
        qvec = self.embed.embed(query)
        if not qvec: return self.recall_fts(query, tier=tier, scope=scope, limit=top_k)
        # Pull all in tier (small datasets) and rank
        q = "SELECT * FROM memory WHERE embedding IS NOT NULL AND tier=?"
        params: list = [tier]
        if scope: q += " AND scope=?"; params.append(scope)
        rows = self.conn.execute(q, params).fetchall()
        scored = []
        for r in rows:
            try:
                v = _f32_load(r["embedding"])
                if len(v) != len(qvec): continue
                sim = _cosine(qvec, v)
                if sim >= min_sim:
                    scored.append((sim, dict(r)))
            except Exception: continue
        scored.sort(key=lambda x: -x[0])
        for _, row in scored[:top_k]:
            self._bump_hit(row["id"])
        return [{**row, "_similarity": sim} for sim, row in scored[:top_k]]

    def list(self, tier: str | None = None, scope: str | None = None,
             limit: int = 50) -> list[dict]:
        q = "SELECT id, tier, scope, key, content, hit_count, created_at, last_used FROM memory"
        clauses = []; params: list = []
        if tier:  clauses.append("tier=?"); params.append(tier)
        if scope: clauses.append("scope=?"); params.append(scope)
        if clauses: q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY hit_count DESC, created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(q, params).fetchall()]

    def delete(self, id_or_key: str, scope: str | None = None) -> bool:
        if scope:
            c = self.conn.execute("DELETE FROM memory WHERE scope=? AND key=?",
                                  (scope, id_or_key))
        else:
            c = self.conn.execute("DELETE FROM memory WHERE id=?", (id_or_key,))
        self.conn.commit()
        return c.rowcount > 0

    def purge_expired(self) -> int:
        now = _now_iso()
        c = self.conn.execute(
            "DELETE FROM memory WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,))
        self.conn.commit()
        return c.rowcount

    def stats(self) -> dict:
        rows = self.conn.execute(
            "SELECT tier, COUNT(*) as n FROM memory GROUP BY tier").fetchall()
        per_tier = {r["tier"]: r["n"] for r in rows}
        total = sum(per_tier.values())
        emb = self.conn.execute(
            "SELECT COUNT(*) FROM memory WHERE embedding IS NOT NULL").fetchone()[0]
        return {"total": total, "per_tier": per_tier, "with_embeddings": emb,
                "db_path": str(self.db_path)}

    def _bump_hit(self, mid: str):
        self.conn.execute(
            "UPDATE memory SET hit_count=hit_count+1, last_used=? WHERE id=?",
            (_now_iso(), mid))
        self.conn.commit()

    def close(self):
        try: self.conn.close()
        except: pass
