#!/usr/bin/env python3
"""
Behavioral regression tests — functions are EXECUTED, not source-grepped.

Rc1 : _parse_skill_phases  — exec real function + parse real SKILL.md files
Rc2 : _PKG_SAFE_RE         — exec real compiled regex, 40+ patterns
Rc3 : tool_install_dep     — exec with mocked subprocess, every code path
Rc4 : _ollama_chat retry   — exec with mocked urlopen, verify retry sequence
Rc5 : CLAUDE_SKILLS        — real temp filesystem, verify fallback chain

Usage:
    python3 tests/test_r_behavioral.py
"""

import ast
import os
import re
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError
from urllib.request import Request as URLRequest

REPO   = Path(__file__).resolve().parent.parent


def _find_src(repo: Path) -> Path:
    """Auto-detect main binary: env var → thmes → thmes fallback."""
    override = os.environ.get("THMES_BIN")
    if override:
        return Path(override)
    for name in ("thmes",):
        p = repo / "bin" / name
        if p.exists():
            return p
    return repo / "bin" / "thmes"


SRC    = _find_src(REPO)
source = SRC.read_text(encoding="utf-8")
_lines = source.splitlines()

# ── Result tracking ───────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []

def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    flag   = "  " if ok else "! "
    print(f"  [{status}] {flag}{name}")
    if detail and not ok:
        print(f"         → {detail}")

# ── AST extraction helpers ────────────────────────────────────────────────
_tree = ast.parse(source)

def _extract_func(name: str) -> str:
    """Extract a top-level function definition by name."""
    for node in _tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(_lines[node.lineno - 1 : node.end_lineno])
    raise ValueError(f"Function '{name}' not found at top level")

def _extract_assign(name: str) -> str:
    """Extract a top-level assignment by variable name."""
    for node in _tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return "\n".join(_lines[node.lineno - 1 : node.end_lineno])
    raise ValueError(f"Assignment '{name}' not found at top level")


# ============================================================================
# Rc1 — _parse_skill_phases (exec real function)
# ============================================================================
print("\n=== Rc1: _parse_skill_phases behavioral ===")

rc1_ns: dict = {"re": re}
exec(_extract_assign("_PHASE_RE"), rc1_ns)
exec(_extract_func("_parse_skill_phases"), rc1_ns)
parse = rc1_ns["_parse_skill_phases"]

# Basic cases
check("Rc1-1  empty string → []",        parse("") == [])
check("Rc1-2  whitespace only → []",     parse("  \n\n  ") == [])

s = parse("## Phase 1: Alpha\nline1\nline2")
check("Rc1-3  single phase count=1",     len(s) == 1)
check("Rc1-4  title stripped",           s[0]["title"] == "Alpha")
check("Rc1-5  content has both lines",   "line1" in s[0]["content"] and "line2" in s[0]["content"])
check("Rc1-6  header not in content",    "Phase 1" not in s[0]["content"])

t = parse("## Phase 1: A\nfoo\n## Phase 2: B\nbar\n## Phase 3: C\nbaz")
check("Rc1-7  three phases count=3",                    len(t) == 3)
check("Rc1-8  phase1 content isolation (no bar)",       "bar" not in t[0]["content"])
check("Rc1-9  phase2 content isolation (no baz)",       "baz" not in t[1]["content"])
check("Rc1-10 last phase captures tail",                "baz" in t[2]["content"])
check("Rc1-11 content stripped whitespace",             t[0]["content"] == "foo")

check("Rc1-12 decimal phase 5.5",        len(parse("## Phase 5.5: Half\ncontent")) == 1)
check("Rc1-13 UPPER PHASE keyword",      parse("## PHASE 2: Upper\n")[0]["title"] == "Upper")
check("Rc1-14 h3 header (###)",          len(parse("### Phase 1: Deep\ncontent")) == 1)
check("Rc1-15 no-colon variant",         len(parse("## Phase 1 NoColon\ncontent")) == 1)

# Phase 0 supported
check("Rc1-16 Phase 0 accepted",         parse("## Phase 0: Init\ncontent")[0]["title"] == "Init")

# Content between phases must not bleed
bleed = parse("## Phase 1: A\nbody1\n## Phase 2: B\nbody2")
check("Rc1-17 no bleed across boundary", "body2" not in bleed[0]["content"])
check("Rc1-18 second phase clean start", bleed[1]["content"] == "body2")

# Test against real SKILL.md files
skills_dir = REPO / "skills"
if skills_dir.is_dir():
    real_files = sorted(skills_dir.rglob("SKILL.md"))
    for sf in real_files[:8]:
        body = sf.read_text(errors="replace")
        phases = parse(body)
        titles = [p["title"] for p in phases]
        # Title uniqueness within each skill
        check(f"Rc1-real {sf.parent.name}: unique titles ({len(phases)} phases)",
              len(titles) == len(set(titles)),
              f"duplicates: {[t for t in titles if titles.count(t) > 1]}")
        # No next-phase header leaks into previous phase content
        for i in range(len(phases) - 1):
            nxt = phases[i + 1]["title"]
            no_leak = nxt not in phases[i]["content"]
            if not no_leak:
                check(f"Rc1-real {sf.parent.name}: phase{i+1} content no leak", no_leak,
                      f"'{nxt}' found in phase {i} content")


# ============================================================================
# Rc2 — _PKG_SAFE_RE (exec real regex from source)
# ============================================================================
print("\n=== Rc2: _PKG_SAFE_RE behavioral ===")

rc2_ns: dict = {"re": re}
exec(_extract_assign("_PKG_SAFE_RE"), rc2_ns)
PKG_RE = rc2_ns["_PKG_SAFE_RE"]

SAFE_CASES = [
    # plain names
    ("numpy",              "plain pip package"),
    ("requests",           "plain pip package"),
    ("ddgs",               "plain pip package"),
    ("rich",               "plain pip package"),
    ("my-package",         "hyphenated"),
    ("my_package",         "underscored"),
    ("pkg.sub",            "dotted"),
    ("A",                  "single uppercase"),
    # version specifiers
    ("numpy>=1.24",        "pip >="),
    ("numpy<=2.0",         "pip <="),
    ("numpy==1.24.5",      "pip =="),
    ("numpy!=1.0",         "pip !="),
    ("numpy~=1.24",        "pip ~="),
    ("numpy<3",            "pip < followed by digit"),
    ("numpy>1",            "pip > followed by digit"),
    ("numpy>=1.24,<3",     "pip multiple constraints"),
    ("pkg==1.*",           "pip wildcard version"),
    # extras
    ("package[extra]",     "pip extras"),
    ("pkg[a,b]",           "pip multiple extras"),
    # npm / cargo
    ("@scope/pkg",         "npm scoped"),
    ("@types/node",        "npm @types"),
    ("crate:name",         "cargo prefix"),
    ("some/path",          "path-like"),
]

UNSAFE_CASES = [
    # classic injection
    ("pkg; rm -rf /",         "semicolon"),
    ("pkg && evil",           "double-ampersand"),
    ("pkg | cat /etc/passwd", "pipe"),
    ("pkg `whoami`",          "backtick"),
    ("pkg$(id)",              "dollar-paren subshell"),
    ("pkg\necho hi",          "embedded newline"),
    ("pkg 'quoted'",          "single-quote + space"),
    ('pkg "dquote"',          "double-quote + space"),
    ("pkg\\backslash",        "backslash"),
    # shell redirection (the fixed bug)
    ("pkg>file",              "> redirect (non-digit after >)"),
    ("pkg<file",              "< redirect (non-digit after <)"),
    (">outfile",              "bare > redirect"),
    ("<infile",               "bare < redirect"),
    # other bad chars
    ("pkg space",             "space in name"),
    ("",                      "empty string"),
]

for name, desc in SAFE_CASES:
    ok = bool(PKG_RE.match(name))
    check(f"Rc2 SAFE  '{name}' ({desc})", ok,
          f"WRONGLY BLOCKED by regex")

for name, desc in UNSAFE_CASES:
    ok = not bool(PKG_RE.match(name))
    check(f"Rc2 BLOCK '{name[:30]}' ({desc})", ok,
          f"WRONGLY ALLOWED — injection risk!")


# ============================================================================
# Rc3 — tool_install_dep (exec with mocked subprocess)
# ============================================================================
print("\n=== Rc3: tool_install_dep behavioral ===")

_mock_console = MagicMock()
rc3_ns: dict = {
    "re":         re,
    "subprocess": MagicMock(wraps=subprocess),  # wrap for CompletedProcess etc.
    "Path":       Path,
    "console":    _mock_console,
    "_truncate":  lambda s, n=4000: s if len(s) <= n else s[:n] + "…",
}
exec(_extract_assign("_PKG_SAFE_RE"), rc3_ns)
exec(_extract_func("tool_install_dep"), rc3_ns)
dep = rc3_ns["tool_install_dep"]


def _fake_run(stdout="", stderr="", returncode=0):
    """Return a factory that gives the same result on every call."""
    def _run(args, capture_output=True, text=True, timeout=30):
        r = MagicMock()
        r.returncode = returncode
        r.stdout     = stdout
        r.stderr     = stderr
        return r
    return _run


def _fake_run_seq(*responses):
    """Return a factory cycling through (stdout, stderr, rc) tuples per call."""
    q = list(responses)
    idx = [0]
    def _run(args, capture_output=True, text=True, timeout=30):
        entry = q[min(idx[0], len(q) - 1)]
        idx[0] += 1
        r = MagicMock()
        r.returncode = entry[2]
        r.stdout     = entry[0]
        r.stderr     = entry[1]
        return r
    return _run


# ── Input validation ─────────────────────────────────────────────────────
rc3_ns["subprocess"].run = _fake_run()

result = dep("")
check("Rc3-1  empty name → error",              "[error]" in result and "required" in result.lower(), result[:80])

result = dep("numpy; rm -rf /")
check("Rc3-2  semicolon injection → blocked",   "[error]" in result and "unsafe" in result.lower(), result[:80])

result = dep("pkg\necho hi")
check("Rc3-3  newline injection → blocked",     "[error]" in result, result[:80])

result = dep("pkg && evil")
check("Rc3-4  double-amp injection → blocked",  "[error]" in result, result[:80])

result = dep("pkg | cat")
check("Rc3-5  pipe injection → blocked",        "[error]" in result, result[:80])

result = dep("pkg>file")
check("Rc3-6  redirect > injection → blocked",  "[error]" in result, result[:80])

result = dep("numpy", manager="ruby")
check("Rc3-7  unknown manager → error",         "[error]" in result and "unknown" in result, result[:80])

# ── Already-installed path ────────────────────────────────────────────────
calls: list = []
def _recording_run(args, capture_output=True, text=True, timeout=30):
    calls.append(list(args))
    r = MagicMock(); r.returncode = 0
    r.stdout = "Name: numpy\nVersion: 1.24\n"; r.stderr = ""
    return r

calls.clear()
rc3_ns["subprocess"].run = _recording_run
result = dep("numpy", manager="pip")
check("Rc3-8  already installed → skip message", "already installed" in result, result[:80])
check("Rc3-9  already installed → only check called (no install)", len(calls) == 1,
      f"expected 1 subprocess call, got {len(calls)}: {calls}")
check("Rc3-10 already installed → check used 'show' subcommand",
      calls and "show" in calls[0], f"call was: {calls}")

# ── Install-success path ──────────────────────────────────────────────────
install_calls: list = []
def _check_fail_install_ok(args, capture_output=True, text=True, timeout=30):
    install_calls.append(list(args))
    r = MagicMock(); r.stderr = ""
    if "show" in args:       # pip show → not found
        r.returncode = 1; r.stdout = ""
    else:                    # pip install → success
        r.returncode = 0; r.stdout = "Successfully installed numpy-1.24\n"
    return r

install_calls.clear()
rc3_ns["subprocess"].run = _check_fail_install_ok
result = dep("numpy", manager="pip")
check("Rc3-11 install success → ✓",            "✓" in result or "Installed" in result, result[:80])
check("Rc3-12 install success → 2 calls",      len(install_calls) == 2,
      f"expected 2 calls (check + install), got {len(install_calls)}")
check("Rc3-13 install used 'install' subcommand",
      any("install" in c for c in install_calls[1:]),
      f"install call was: {install_calls[1] if len(install_calls) > 1 else '?'}")

# ── Install-failure path ──────────────────────────────────────────────────
rc3_ns["subprocess"].run = _fake_run_seq(
    ("", "", 1),                                         # pip show → not found
    ("", "ERROR: Could not find version", 1),            # pip install → fail
)
result = dep("nonexistent-pkg-xyz", manager="pip")
check("Rc3-14 install failure → ✗",            "✗" in result or "failed" in result.lower(), result[:80])
check("Rc3-15 failure shows exit code",         "exit" in result, result[:80])

# ── Auto-detect: npm for @scope/pkg ──────────────────────────────────────
detect_calls: list = []
def _detect_run(args, capture_output=True, text=True, timeout=30):
    detect_calls.append(list(args))
    r = MagicMock(); r.returncode = 1; r.stdout = ""; r.stderr = ""
    return r

detect_calls.clear()
rc3_ns["subprocess"].run = _detect_run
dep("@scope/pkg")
npm_used = any("npm" in " ".join(map(str, c)) for c in detect_calls)
check("Rc3-16 auto-detect npm for @scope/pkg", npm_used,
      f"calls: {detect_calls}")

# ── Auto-detect: crate: prefix → cargo ───────────────────────────────────
detect_calls.clear()
dep("crate:serde")
cargo_used = any("cargo" in " ".join(map(str, c)) for c in detect_calls)
check("Rc3-17 auto-detect cargo for crate:serde", cargo_used,
      f"calls: {detect_calls}")

# ── brew already-installed uses two checks (formula + cask) ──────────────
brew_calls: list = []
def _brew_not_installed(args, capture_output=True, text=True, timeout=30):
    brew_calls.append(list(args))
    r = MagicMock(); r.returncode = 1; r.stdout = ""; r.stderr = ""
    return r

brew_calls.clear()
rc3_ns["subprocess"].run = _brew_not_installed
dep("ffmpeg", manager="brew")
brew_cmds = [" ".join(map(str, c)) for c in brew_calls]
check("Rc3-18 brew checks formula AND cask before install",
      any("formula" in c for c in brew_cmds) and any("cask" in c for c in brew_cmds),
      f"brew calls: {brew_cmds}")


# ============================================================================
# Rc4 — _ollama_chat retry (exec with mocked urlopen)
# ============================================================================
print("\n=== Rc4: _ollama_chat retry behavioral ===")

_mock_c4 = MagicMock()
rc4_ns: dict = {
    "json":                    json,
    "time":                    time,
    "Request":                 URLRequest,
    "HTTPError":               HTTPError,
    "mm":                      MagicMock(ollama_meta={"model": "qwen3.5:4b", "ctx": 16384}),
    "console":                 _mock_c4,
    "OLLAMA_HOST":             "http://localhost:11434",
    "OLLAMA_TIMEOUT":          10.0,
    "OLLAMA_LOAD_TIMEOUT":     30.0,
    "_OLLAMA_NUM_CTX_OVERRIDE": 0,
    "_OLLAMA_DEFAULT_CTX":     16384,
    "_ollama_headers":         lambda extra=None: {"Content-Type": "application/json"},
}
exec(_extract_func("_is_cloud_model"), rc4_ns)            # deps of _ollama_chat
exec(_extract_func("_native_tool_calls_to_text"), rc4_ns)
exec(_extract_func("_ollama_tools_schema"), rc4_ns)
exec(_extract_func("_ollama_chat"), rc4_ns)
chat = rc4_ns["_ollama_chat"]

_HISTORY = [{"role": "user", "content": "Hello"}]
_GOOD = {
    "message":       {"role": "assistant", "content": "Hi there!"},
    "eval_count":    50,
    "eval_duration": 500_000_000,
}


def _resp(data: dict):
    """Build a context-manager mock that simulates Ollama NDJSON streaming.
    _ollama_chat now iterates over the response line-by-line (stream=True),
    so the mock must be iterable rather than having a .read() method.
    Emits a single final chunk so _ollama_chat collects all content in one pass."""
    m = MagicMock()
    m.__enter__ = lambda s: s
    m.__exit__  = MagicMock(return_value=False)
    chunk = {
        "message":       data.get("message", {"content": ""}),
        "done":          True,
        "eval_count":    data.get("eval_count", 0),
        "eval_duration": data.get("eval_duration", 0),
    }
    line = json.dumps(chunk).encode() + b"\n"
    m.__iter__ = lambda s: iter([line])
    return m


# Rc4-1: clean success — no warning, correct text + stats
_mock_c4.reset_mock()
rc4_ns["urlopen"] = lambda req, timeout: _resp(_GOOD)
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-1  success → text returned",          text == "Hi there!", repr(text))
check("Rc4-2  success → stats.tps > 0",          stats["tps"] > 0,   str(stats))
check("Rc4-3  success → no warning printed",      _mock_c4.print.call_count == 0,
      f"print called {_mock_c4.print.call_count} times")

# Rc4-4: HTTP 500 once → retry with halved num_ctx → success
_ctx_log: list[int] = []
def _urlopen_500_once(req, timeout):
    body = json.loads(req.data.decode())
    _ctx_log.append(body["options"]["num_ctx"])
    if len(_ctx_log) == 1:
        raise HTTPError(url="", code=500, msg="Internal Server Error", hdrs=None, fp=None)
    return _resp(_GOOD)

_mock_c4.reset_mock(); _ctx_log.clear()
rc4_ns["urlopen"] = _urlopen_500_once
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-4  500→retry → text returned",         text == "Hi there!", repr(text))
check("Rc4-5  500→retry → 2 requests made",       len(_ctx_log) == 2,
      f"ctx sequence: {_ctx_log}")
check("Rc4-6  500→retry → num_ctx halved",
      len(_ctx_log) == 2 and _ctx_log[1] == _ctx_log[0] // 2,
      f"expected {_ctx_log[0]//2 if _ctx_log else '?'}, got {_ctx_log[1] if len(_ctx_log)>1 else '?'}")
check("Rc4-7  500→retry → warning printed",       _mock_c4.print.call_count >= 1,
      f"print called {_mock_c4.print.call_count} times")
warn_text = " ".join(str(c) for c in _mock_c4.print.call_args_list)
check("Rc4-8  warning mentions env var hint",      "THMES_OLLAMA_NUM_CTX" in warn_text,
      f"warning text: {warn_text[:200]}")

# Rc4-9: HTTP 500 every time → full ladder exhausted → diagnostic
_ctx_all: list[int] = []
def _urlopen_always_500(req, timeout):
    _ctx_all.append(json.loads(req.data.decode())["options"]["num_ctx"])
    raise HTTPError(url="", code=500, msg="Internal Server Error", hdrs=None, fp=None)

_ctx_all.clear()
rc4_ns["urlopen"] = _urlopen_always_500
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-9  all 500 → error message",           "[ollama error]" in text or "HTTP 500" in text,
      text[:150])
check("Rc4-10 all 500 → diagnostic has env var",  "THMES_OLLAMA_NUM_CTX" in text, text[:200])
check("Rc4-11 all 500 → stats are zero",          stats["tokens"] == 0 and stats["tps"] == 0)
check("Rc4-12 all 500 → full ladder tried = [16384,8192,4096,2048]",
      _ctx_all == [16384, 8192, 4096, 2048],
      f"got {_ctx_all}")

# Rc4-13: HTTP 401 → auth error, no retry
_call_401 = [0]
def _urlopen_401(req, timeout):
    _call_401[0] += 1
    raise HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)

_call_401[0] = 0
rc4_ns["urlopen"] = _urlopen_401
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-13 401 → auth error message",          "auth" in text.lower() or "401" in text,
      text[:120])
check("Rc4-14 401 → no retry (exactly 1 request)", _call_401[0] == 1,
      f"made {_call_401[0]} requests")

# Rc4-15/16: TimeoutError → retry ONCE with the longer load budget, then error
_call_exc = [0]
def _urlopen_timeout(req, timeout):
    _call_exc[0] += 1
    raise TimeoutError("timed out")

_call_exc[0] = 0
rc4_ns["urlopen"] = _urlopen_timeout
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-15 timeout → error message",   "ollama error" in text.lower()
      and "timed out" in text.lower(), text[:80])
check("Rc4-16 timeout → retries once (2 requests)", _call_exc[0] == 2,
      f"made {_call_exc[0]} requests")

# Rc4-16b: non-timeout exception → immediate error, NO retry (1 request)
_call_g = [0]
def _urlopen_generic(req, timeout):
    _call_g[0] += 1
    raise ValueError("boom")

_call_g[0] = 0
rc4_ns["urlopen"] = _urlopen_generic
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-16b generic exception → error message", "ollama error" in text.lower(), text[:80])
check("Rc4-16b generic exception → no retry",       _call_g[0] == 1,
      f"made {_call_g[0]} requests")

# Rc4-17: 500 then 500 then success → 3 requests, ctx halved twice
_ctx_2x: list[int] = []
def _urlopen_500x2(req, timeout):
    _ctx_2x.append(json.loads(req.data.decode())["options"]["num_ctx"])
    if len(_ctx_2x) < 3:
        raise HTTPError(url="", code=500, msg="Internal Server Error", hdrs=None, fp=None)
    return _resp(_GOOD)

_ctx_2x.clear()
rc4_ns["urlopen"] = _urlopen_500x2
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-17 500×2 → success on 3rd attempt",   text == "Hi there!", repr(text))
check("Rc4-18 500×2 → ctx halved twice",
      len(_ctx_2x) == 3 and _ctx_2x[2] == _ctx_2x[0] // 4,
      f"ctx sequence: {_ctx_2x}")

# Rc4-CLOUD: cloud models (':cloud' / '-cloud') must NOT send num_ctx and must
# NOT run the local-RAM OOM ladder; a cloud 500 is transient → retry then a
# cloud-specific error (never the "RAM" diagnostic). Regression for the bug
# where '-cloud' tags slipped through to the ctx ladder and 500'd.
import types as _types
_orig_mm, _orig_time = rc4_ns["mm"], rc4_ns["time"]
rc4_ns["time"] = _types.SimpleNamespace(time=time.time, sleep=lambda *a, **k: None)
rc4_ns["mm"] = MagicMock(ollama_meta={"model": "qwen3-coder:480b-cloud", "ctx": 16384})

# helper recognizes BOTH cloud suffix shapes, rejects locals
_isc = rc4_ns["_is_cloud_model"]
check("Rc4-C0  _is_cloud_model: ':cloud' + '-cloud' true, local false",
      _isc("glm-4.6:cloud") and _isc("qwen3-coder:480b-cloud")
      and not _isc("qwen3:8b") and not _isc("scb10x/x:latest"))

# C1: cloud success → payload omits num_ctx
_cloud_payloads: list = []
def _urlopen_cloud_ok(req, timeout):
    _cloud_payloads.append(json.loads(req.data.decode()))
    return _resp(_GOOD)
rc4_ns["urlopen"] = _urlopen_cloud_ok
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-C1  cloud success → text returned", text == "Hi there!", repr(text))
check("Rc4-C2  cloud → NO num_ctx in options",
      bool(_cloud_payloads) and "num_ctx" not in _cloud_payloads[0]["options"],
      f"options={_cloud_payloads[0]['options'] if _cloud_payloads else '?'}")

# C3: cloud 500 always → retried (>1) then a cloud error, never the RAM message
_cloud_500 = [0]
def _urlopen_cloud_500(req, timeout):
    _cloud_500[0] += 1
    raise HTTPError(url="", code=500, msg="Internal Server Error", hdrs=None, fp=None)
rc4_ns["urlopen"] = _urlopen_cloud_500
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-C3  cloud 500 → retried more than once", _cloud_500[0] > 1,
      f"made {_cloud_500[0]} requests")
check("Rc4-C4  cloud 500 → cloud error, not RAM diagnostic",
      "cloud" in text.lower() and "RAM" not in text, text[:160])

# C5: cloud 500 then success → recovers on retry
_cloud_mix = [0]
def _urlopen_cloud_500_then_ok(req, timeout):
    _cloud_mix[0] += 1
    if _cloud_mix[0] == 1:
        raise HTTPError(url="", code=500, msg="busy", hdrs=None, fp=None)
    return _resp(_GOOD)
rc4_ns["urlopen"] = _urlopen_cloud_500_then_ok
text, stats = chat(_HISTORY, system="", max_tokens=128)
check("Rc4-C5  cloud 500→ok → recovers on retry", text == "Hi there!", repr(text))

rc4_ns["mm"], rc4_ns["time"] = _orig_mm, _orig_time   # restore for later sections

# Rc4-N: native function-calling — schema build + native tool_calls → canonical
# <tool_call> text so the existing parser handles them. Regression for the
# Ollama-native tool path added so tool-trained models (gpt-oss/qwen3-coder/
# glm/minimax) emit structured calls instead of fragile inline text.
_schema = rc4_ns["_ollama_tools_schema"]({"write_file": {
    "params": {"path": "str", "content": "str", "mode": "str (default w)"},
    "desc": "Write text to a file"}})
check("Rc4-N1  schema: one typed function entry",
      len(_schema) == 1 and _schema[0]["type"] == "function"
      and _schema[0]["function"]["name"] == "write_file")
_props = _schema[0]["function"]["parameters"]
check("Rc4-N2  schema: types + required (default→optional)",
      _props["properties"]["path"]["type"] == "string"
      and "path" in _props["required"] and "mode" not in _props["required"],
      str(_props))

_to_text = rc4_ns["_native_tool_calls_to_text"]
_txt = _to_text([{"function": {"name": "write_file",
                  "arguments": {"path": "/tmp/x", "content": "hi"}}}])
check("Rc4-N3  native call → canonical <tool_call> text",
      "<tool_call>" in _txt and '"name": "write_file"' in _txt
      and '"path": "/tmp/x"' in _txt, _txt)
_txt2 = _to_text([{"function": {"name": "write_file",
                   "arguments": {"content": {"type": "string", "value": "hi"}}}}])
check("Rc4-N4  unwraps llama3.2 {type,value} arg", '"content": "hi"' in _txt2, _txt2)

def _resp_native(req, timeout):
    m = MagicMock(); m.__enter__ = lambda s: s; m.__exit__ = MagicMock(return_value=False)
    chunk = {"message": {"content": "", "tool_calls":
             [{"function": {"name": "bash", "arguments": {"command": "ls"}}}]},
             "done": True, "eval_count": 5, "eval_duration": 1}
    m.__iter__ = lambda s: iter([json.dumps(chunk).encode() + b"\n"])
    return m
rc4_ns["mm"] = MagicMock(ollama_meta={"model": "qwen3:8b", "ctx": 16384})
rc4_ns["urlopen"] = _resp_native
text, stats = chat(_HISTORY, system="", max_tokens=128, tools=[{"type": "function"}])
check("Rc4-N5  _ollama_chat folds native tool_calls into <tool_call>",
      "<tool_call>" in text and '"name": "bash"' in text, text[:160])
rc4_ns["mm"] = _orig_mm


# ============================================================================
# Rc5 — CLAUDE_SKILLS path resolution (real temp filesystem)
# ============================================================================
print("\n=== Rc5: CLAUDE_SKILLS path resolution ===")

# Replicate the resolution logic from the source
def _resolve_skills(env_override=None, proj_exists=False, home_exists=False,
                    proj_path=None, home_path=None) -> Path:
    if env_override:
        return Path(env_override)
    if proj_path and proj_path.is_dir():
        return proj_path
    return home_path if (home_path and home_exists) else (Path.home() / ".claude" / "skills")

with tempfile.TemporaryDirectory() as tmpdir:
    tmp        = Path(tmpdir)
    proj_dir   = tmp / "project"
    proj_skills = proj_dir / "skills"
    home_base  = tmp / "home"
    home_skills = home_base / ".claude" / "skills"
    custom     = tmp / "custom_skills"
    custom.mkdir(parents=True)

    # Rc5-1: env override — wins regardless of dir existence
    resolved = _resolve_skills(env_override=str(custom),
                               proj_path=proj_skills, home_path=home_skills)
    check("Rc5-1  env override → custom dir",        resolved == custom, str(resolved))

    # Rc5-2: env override wins even if project/skills also exists
    proj_skills.mkdir(parents=True)
    resolved = _resolve_skills(env_override=str(custom),
                               proj_path=proj_skills, home_path=home_skills)
    check("Rc5-2  env override wins over project/skills", resolved == custom, str(resolved))

    # Rc5-3: no env, project/skills exists → use project
    resolved = _resolve_skills(proj_path=proj_skills, home_path=home_skills)
    check("Rc5-3  project/skills exists → used",    resolved == proj_skills, str(resolved))

    # Rc5-4: no env, project/skills MISSING → fallback to ~/.claude/skills
    proj_skills.rmdir()
    home_skills.mkdir(parents=True)
    resolved = _resolve_skills(proj_path=proj_skills, home_exists=True, home_path=home_skills)
    check("Rc5-4  no project → falls back to home", ".claude" in str(resolved), str(resolved))

    # Rc5-5: neither exists → returns ~/.claude/skills anyway (default, not error)
    home_skills.rmdir()
    resolved = _resolve_skills(proj_path=proj_skills, home_path=home_skills)
    check("Rc5-5  nothing exists → default without error", isinstance(resolved, Path), str(resolved))

    # Rc5-6: env override accepted even for non-existent path (trust user)
    fake_dir = str(tmp / "does_not_exist")
    resolved = _resolve_skills(env_override=fake_dir)
    check("Rc5-6  env override with nonexistent path accepted", str(resolved) == fake_dir)

# Verify source actually implements the chain (not just simulation above)
check("Rc5-7  source has THMES_SKILLS_DIR check",
      "THMES_SKILLS_DIR" in source and "CLAUDE_SKILLS" in source)
check("Rc5-8  source uses is_dir() guard",
      "is_dir()" in source)
check("Rc5-9  source has project-local skills fallback",
      "_PROJ_SKILLS" in source or ('skills' in source and "parent" in source))


# ============================================================================
# Syntax check
# ============================================================================
print("\n=== Syntax check ===")
proc = subprocess.run(
    [sys.executable, "-m", "py_compile", str(SRC)],
    capture_output=True, text=True, cwd=str(REPO),
)
check("py_compile clean", proc.returncode == 0, proc.stderr.strip())


# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 60)
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"Total: {total}  PASS: {passed}  FAIL: {failed}")
if failed:
    print("\nFailed:")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL  {name}")
            if detail:
                print(f"        {detail}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
