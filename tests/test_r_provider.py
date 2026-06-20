#!/usr/bin/env python3
"""
Provider-resilience tests — the Ollama ctx-adaptation layer that prevents the
"forced model reload → timeout" class of bug. Functions are EXECUTED with a
mocked urlopen (no network), not source-grepped.

Rp1 : _ollama_ps           — parse /api/ps → {tag: context_length}; safe on error
Rp2 : _ollama_resolve_ctx  — env override wins · reuse loaded ctx (no reload) ·
                             fall back to family ctx when not loaded / probe fails

Usage:
    python3 tests/test_r_provider.py
"""
import ast
import io
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _find_src(repo: Path) -> Path:
    override = os.environ.get("THMES_BIN")
    if override:
        return Path(override)
    for name in ("thmes",):
        p = repo / "bin" / name
        if p.exists():
            return p
    return repo / "bin" / "thmes"


SRC = _find_src(REPO)
source = SRC.read_text(encoding="utf-8")
_lines = source.splitlines()
_tree = ast.parse(source)

results: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {'  ' if ok else '! '}{name}")
    if detail and not ok:
        print(f"         → {detail}")


def _seg(name: str) -> str:
    for node in _tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(_lines[node.lineno - 1: node.end_lineno])
    raise ValueError(f"{name!r} not found")


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


ns: dict = {
    "json": json,
    "Request": lambda *a, **k: ("REQ", a, k),
    "OLLAMA_HOST": "http://localhost:11434",
    "_OLLAMA_NUM_CTX_OVERRIDE": 0,
    "_OLLAMA_DEFAULT_CTX": 16384,
    "_ollama_headers": lambda extra=None: {},
    "console": type("C", (), {"print": staticmethod(lambda *a, **k: None)})(),
}
for _n in ("_ollama_ps", "_ollama_resolve_ctx"):
    exec(compile(_seg(_n), str(SRC), "exec"), ns)
_ollama_ps = ns["_ollama_ps"]
_ollama_resolve_ctx = ns["_ollama_resolve_ctx"]

print("Provider resilience — ctx adaptation tests")
print("=" * 60)

# ── Rp1: _ollama_ps ─────────────────────────────────────────────────────────
print("\nRp1: _ollama_ps")
_PS_JSON = json.dumps({"models": [
    {"name": "gemma4:e4b", "model": "gemma4:e4b", "context_length": 32768},
    {"name": "qwen3:8b",  "model": "qwen3:8b",  "context_length": 16384},
]}).encode()
ns["urlopen"] = lambda req, timeout=2.0: _Resp(_PS_JSON)
ps = _ollama_ps()
check("Rp1-1 parses loaded models", ps.get("gemma4:e4b") == 32768, f"got {ps}")
check("Rp1-2 multiple models", ps.get("qwen3:8b") == 16384, f"got {ps}")

def _boom(req, timeout=2.0):
    raise OSError("connection refused")
ns["urlopen"] = _boom
check("Rp1-3 network error → empty dict (safe)", _ollama_ps() == {})

# ── Rp2: _ollama_resolve_ctx ────────────────────────────────────────────────
print("\nRp2: _ollama_resolve_ctx")

# (a) env override wins over everything
ns["urlopen"] = lambda req, timeout=2.0: _Resp(_PS_JSON)
ns["_OLLAMA_NUM_CTX_OVERRIDE"] = 8192
meta = {"model": "gemma4:e4b", "ctx": 32768}
got = _ollama_resolve_ctx(meta)
check("Rp2-1 env override wins", got == 8192 and meta["ctx"] == 8192, f"got {got}")

# (b) model already resident → reuse its loaded ctx (avoid reload)
ns["_OLLAMA_NUM_CTX_OVERRIDE"] = 0
meta = {"model": "gemma4:e4b", "ctx": 8192}   # our guess differs from loaded
got = _ollama_resolve_ctx(meta)
check("Rp2-2 reuse loaded ctx (no reload)", got == 32768 and meta["ctx"] == 32768,
      f"got {got}, meta={meta}")

# (c) model NOT resident → keep our family-heuristic ctx
meta = {"model": "llama3.2:3b", "ctx": 32768}
got = _ollama_resolve_ctx(meta)
check("Rp2-3 not loaded → keep family ctx", got == 32768, f"got {got}")

# (d) probe fails → keep family ctx
ns["urlopen"] = _boom
meta = {"model": "gemma4:e4b", "ctx": 16384}
got = _ollama_resolve_ctx(meta)
check("Rp2-4 ps probe fails → keep family ctx", got == 16384, f"got {got}")

# ── Rp3: _detect_model_profile uses real Ollama family, not the name ─────────
print("\nRp3: _detect_model_profile (tool-call format)")
import types as _types
pns = {"re": re,
       "_parse_param_size": None, "_chunk_chars_for_size": None,
       "_family_from_string": None,
       "ModelProfile": lambda **kw: _types.SimpleNamespace(**kw)}
for _n in ("_family_from_string", "_parse_param_size", "_chunk_chars_for_size",
           "_detect_model_profile"):
    exec(compile(_seg(_n), str(SRC), "exec"), pns)
detect = pns["_detect_model_profile"]

# mistral:7b is really a llama-arch model in Ollama → must NOT get mistral fmt
mm = _types.SimpleNamespace(name="ol:mistral:7b", backend="ollama",
                            ollama_meta={"family": "llama"})
p = detect(mm)
check("Rp3-1 mistral:7b (real llama) → pythontag, not mistral",
      p.fmt == "pythontag" and p.source == "ollama-meta", f"got fmt={p.fmt} src={p.source}")

# custom-named qwen fine-tune → xml via real family
mm = _types.SimpleNamespace(name="ol:super-assistant:latest", backend="ollama",
                            ollama_meta={"family": "qwen2"})
p = detect(mm)
check("Rp3-2 custom name + real qwen2 → xml", p.fmt == "xml", f"got {p.fmt}")

# gemma stays xml
mm = _types.SimpleNamespace(name="ol:gemma4:e4b", backend="ollama",
                            ollama_meta={"family": "gemma4"})
check("Rp3-3 gemma4 → xml", detect(mm).fmt == "xml")

# MLX (no ollama_meta) → name heuristic fallback
mm = _types.SimpleNamespace(name="gemma", backend="mlx-vlm", ollama_meta={})
p = detect(mm)
check("Rp3-4 MLX falls back to name heuristic", p.fmt == "xml" and p.source == "name-heuristic",
      f"got fmt={p.fmt} src={p.source}")

# missing family → name heuristic
mm = _types.SimpleNamespace(name="ol:qwen3:8b", backend="ollama", ollama_meta={})
check("Rp3-5 ollama w/o family → name heuristic", detect(mm).source == "name-heuristic")

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Total: {total}  PASS: {passed}  FAIL: {total - passed}")
print("=" * 60)
sys.exit(0 if passed == total else 1)
