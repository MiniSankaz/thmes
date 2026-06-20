#!/usr/bin/env python3
"""
Behavioral tests for the deterministic research controller — functions are
EXECUTED with stubbed deps (no mlx, no network), not source-grepped.

Rr1 : _detect_uncertainty   — TH + EN knowledge-gap phrases vs benign hedging
Rr2 : _extract_domains      — pull unique domains from search/fetch output
Rr3 : _expand_keywords      — heuristic fallback dedups vs already-tried
Rr4 : run_research_loop     — loops, expands keywords when thin, stops at depth,
                              synthesizes over gathered evidence

Usage:
    python3 tests/test_r_research_loop.py
"""
import ast
import os
import re
import sys
import time
import types
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
    flag = "  " if ok else "! "
    print(f"  [{status}] {flag}{name}")
    if detail and not ok:
        print(f"         → {detail}")


def _seg(name: str) -> str:
    """Source text of a top-level def OR assignment, by name."""
    for node in _tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(_lines[node.lineno - 1: node.end_lineno])
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return "\n".join(_lines[node.lineno - 1: node.end_lineno])
    raise ValueError(f"{name!r} not found at top level")


# ── Build an isolated namespace with stubbed module deps ────────────────────
def _domain_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return (urlparse(url).hostname or "").lower().lstrip("www.")
    except Exception:
        return ""


ns: dict = {
    "re": re,
    "os": os,
    "time": time,
    "_THAI_RE": re.compile(r"[฀-๿]"),
    "console": types.SimpleNamespace(print=lambda *a, **k: None),
    "_FLAGS": {"research_depth": 3, "research_rounds": 3, "research_kw_llm": False},
    "_domain_of": _domain_of,
    "_truncate": lambda s, n=4000: (s or "")[:n],
    "_strip_model_artifacts": lambda s: s,
    "TOOL_CALL_RE": re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL),
    "current_datetime_context": lambda: "NOW",
    "DEFAULT_MAX_TOKENS": 512,
    "_build_search_angles": lambda *a, **k: [],
    "_extract_finance_entity": lambda q: None,
    "Optional": __import__("typing").Optional,
}

# exec the REAL implementations in dependency order
for _name in ("_env", "_URL_IN_TEXT_RE", "_extract_domains",
              "_UNCERTAINTY_RE", "_detect_uncertainty",
              "_expand_keywords", "_SYNTH_CORPUS_BUDGET", "_SYNTH_BLOCK_CAP",
              "_SYNTH_MAX_TOKENS", "_evidence_digest", "_synthesize_research",
              "run_research_loop"):
    exec(compile(_seg(_name), str(SRC), "exec"), ns)

_detect_uncertainty = ns["_detect_uncertainty"]
_extract_domains = ns["_extract_domains"]
_expand_keywords = ns["_expand_keywords"]
run_research_loop = ns["run_research_loop"]

print("Research controller — behavioral tests")
print("=" * 60)

# ── Rr1: _detect_uncertainty ───────────────────────────────────────────────
print("\nRr1: _detect_uncertainty")
check("Rr1-1 TH 'ไม่แน่ใจ' fires",
      bool(_detect_uncertainty("ฉันไม่แน่ใจเรื่องราคาล่าสุดครับ")))
check("Rr1-2 TH 'ไม่มีข้อมูล' fires",
      bool(_detect_uncertainty("ผมไม่มีข้อมูลเกี่ยวกับเรื่องนี้")))
check("Rr1-3 TH 'อาจไม่เป็นปัจจุบัน' fires",
      bool(_detect_uncertainty("ข้อมูลของฉันอาจไม่เป็นปัจจุบัน")))
check("Rr1-4 EN 'I'm not sure' fires",
      bool(_detect_uncertainty("I'm not sure about the current price.")))
check("Rr1-5 EN 'as of my training' fires",
      bool(_detect_uncertainty("As of my training data, it was around $40k.")))
check("Rr1-6 EN 'I don't have real-time' fires",
      bool(_detect_uncertainty("I don't have real-time access to that.")))
check("Rr1-7 benign answer does NOT fire",
      _detect_uncertainty("Bitcoin is a decentralized cryptocurrency.") is None)
check("Rr1-8 confident TH answer does NOT fire",
      _detect_uncertainty("ราคาทองวันนี้คือ 42,000 บาทต่อบาททองคำ") is None)
check("Rr1-9 empty/None safe",
      _detect_uncertainty("") is None and _detect_uncertainty(None) is None)

# ── Rr2: _extract_domains ──────────────────────────────────────────────────
print("\nRr2: _extract_domains")
sample = ("1. Title (cnn.com)\n   https://www.cnn.com/article-1\n"
          "2. Other\n   https://reuters.com/news/x?q=2 snippet\n"
          "see also http://cnn.com/dupe and (https://bbc.co.uk/news).")
doms = _extract_domains(sample)
check("Rr2-1 finds cnn.com", "cnn.com" in doms)
check("Rr2-2 finds reuters.com", "reuters.com" in doms)
check("Rr2-3 finds bbc.co.uk", "bbc.co.uk" in doms)
check("Rr2-4 dedups www + dupe → 3 unique", len(doms) == 3, f"got {sorted(doms)}")
check("Rr2-5 empty text → empty set", _extract_domains("") == set())

# ── Rr3: _expand_keywords (heuristic, allow_model=False) ───────────────────
print("\nRr3: _expand_keywords")
fake_an = types.SimpleNamespace(search_angles=["bitcoin price", "ราคา bitcoin"])
exp = _expand_keywords("bitcoin price", tried=["bitcoin price"],
                       analysis=fake_an, allow_model=False, n=3)
check("Rr3-1 returns up to n", 0 < len(exp) <= 3, f"got {exp}")
check("Rr3-2 excludes already-tried",
      "bitcoin price" not in [e.lower() for e in exp], f"got {exp}")
check("Rr3-3 all unique", len(exp) == len({e.lower() for e in exp}))

# ── Rr4: run_research_loop (mocked search + synthesis) ─────────────────────
print("\nRr4: run_research_loop")

_search_calls: list = []


def _fake_search(query, max_results=5, *, mode="text", timelimit=None,
                 region=None, auto_fetch=False):
    _search_calls.append(query)
    # each DISTINCT query yields one unique source domain
    slug = re.sub(r"[^a-z0-9]+", "", query.lower())[:12] or "x"
    return f"1. result for {query}\n   https://{slug}.example.org/page snippet text"


def _fake_generate(history, system, *, image=None, audio=None, max_tokens=512):
    # _synthesize_research is the only caller here (allow_model_keywords=False)
    return ("SYNTH: answer citing [src.example.org]", {"tokens": 5, "tps": 1.0})


ns["tool_web_search"] = _fake_search
ns["generate_reply"] = _fake_generate
ns["_analyze_prompt"] = lambda q: an

an = types.SimpleNamespace(language="en", time_sensitive=False, domain="general",
                           intent="factual",
                           search_angles=["alpha topic", "beta topic"])

ans, meta = run_research_loop("alpha topic", depth=3, max_rounds=3,
                              analysis=an, allow_model_keywords=False)

check("Rr4-1 returns synthesized answer", ans.startswith("SYNTH:"), f"got {ans!r}")
check("Rr4-2 reached depth ≥3 sources", meta["n_sources"] >= 3,
      f"sources={meta['n_sources']}")
check("Rr4-3 looped ≥2 rounds (expanded keywords)", meta["rounds"] >= 2,
      f"rounds={meta['rounds']}")
check("Rr4-4 searched >2 distinct queries (initial 2 + expansions)",
      len(set(_search_calls)) > 2, f"queries={_search_calls}")
check("Rr4-5 meta lists gathered domains",
      meta["n_sources"] == len(meta["domains"]))

# stops cleanly when nothing is found (empty search results → no domains)
_search_calls.clear()
ns["tool_web_search"] = lambda *a, **k: "(no results)"
an2 = types.SimpleNamespace(language="en", time_sensitive=False, domain="general",
                            intent="factual", search_angles=["zzz"])
ans2, meta2 = run_research_loop("zzz", depth=3, max_rounds=3, analysis=an2,
                                allow_model_keywords=False)
check("Rr4-6 no-results run terminates (stagnation guard)", meta2["rounds"] <= 3,
      f"rounds={meta2['rounds']}")
check("Rr4-7 no-results → 0 sources", meta2["n_sources"] == 0)

# ── Rr5: synthesis degrades to a sources digest when the model errors ───────
print("\nRr5: synthesis fallback")
_synthesize_research = ns["_synthesize_research"]
ns["generate_reply"] = lambda *a, **k: ("[ollama error] TimeoutError: timed out",
                                        {"tokens": 0})
ev_real = [("gold price today",
            "1. Gold update (reuters.com)\n   https://reuters.com/markets/gold\n"
            "   Spot gold traded near $2,350/oz on June 10, 2026.")]
digest = _synthesize_research("gold price today", ev_real, lang="en")
check("Rr5-1 model error → non-empty fallback", bool(digest), f"got {digest!r}")
check("Rr5-2 fallback does NOT leak raw ollama error",
      "[ollama error]" not in digest, f"got {digest!r}")
check("Rr5-3 fallback cites the source domain", "reuters.com" in digest,
      f"got {digest!r}")

# ── Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Total: {total}  PASS: {passed}  FAIL: {total - passed}")
print("=" * 60)
sys.exit(0 if passed == total else 1)
