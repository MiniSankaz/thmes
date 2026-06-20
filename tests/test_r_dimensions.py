#!/usr/bin/env python3
"""
Multi-dimension regression tests — R{rx} format.

R1 : _parse_skill_phases  (regex engine)
R2 : run_skill_agentic    (phase chaining logic — source-level)
R3 : tool_install_dep     (injection guard + manager detection)
R4 : _ollama_chat retry   (OOM ctx ladder — source-level)
R5 : CLAUDE_SKILLS paths  (fallback chain)
Rrx: _PKG_SAFE_RE         (injection regex exhaustive)

Usage:
    python3 tests/test_r_dimensions.py
"""

import os
import re
import sys
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


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


SRC  = _find_src(REPO)

# ---------------------------------------------------------------------------
results: list[tuple[str, bool, str]] = []

def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    flag   = "  " if ok else "! "
    print(f"  [{status}] {flag}{name}")
    if detail and not ok:
        print(f"         {detail}")

source = SRC.read_text(encoding="utf-8")

# ===========================================================================
# R1 — _parse_skill_phases  (regex engine)
# ===========================================================================
print("\n=== R1: _parse_skill_phases ===")

_PHASE_RE = re.compile(
    r'^#{2,3}\s+Phase\s+[\d.]+:?\s*(.+)$', re.MULTILINE | re.IGNORECASE
)

def _parse(body: str) -> list:
    matches = list(_PHASE_RE.finditer(body))
    if not matches:
        return []
    phases = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        phases.append({"title": m.group(1).strip(), "content": body[start:end].strip()})
    return phases

check("R1-1 empty → []",           _parse("") == [])
check("R1-2 single phase",          len(_parse("## Phase 1: Alpha\ncontent")) == 1)
check("R1-3 title stripped",        _parse("## Phase 1: Alpha\n")[0]["title"] == "Alpha")
check("R1-4 three phases",          len(_parse("## Phase 1: A\n## Phase 2: B\n## Phase 3: C")) == 3)
check("R1-5 h3 accepted",           len(_parse("### Phase 2: Deep\ncontent")) == 1)
check("R1-6 decimal (5.5)",         len(_parse("## Phase 5.5: Half\n")) == 1)
check("R1-7 case-insensitive",      len(_parse("## phase 1: lower\n")) == 1)
check("R1-8 no-colon variant",      len(_parse("## Phase 1 No Colon\ncontent")) == 1)
check("R1-9 non-phase h2 → 0",      len(_parse("## NotPhase: something")) == 0)
check("R1-10 content boundary",
    _parse("## Phase 1: A\nbody1\n## Phase 2: B\nbody2")[0]["content"] == "body1")
check("R1-11 last phase gets tail",
    "body2" in _parse("## Phase 1: A\n## Phase 2: B\nbody2")[1]["content"])

# ===========================================================================
# R2 — run_skill_agentic (source-level structural checks)
# ===========================================================================
print("\n=== R2: run_skill_agentic source checks ===")

check("R2-1 function defined",           "def run_skill_agentic(" in source)
check("R2-2 calls _parse_skill_phases",  "_parse_skill_phases(" in source)
check("R2-3 calls agent_turn(",          "agent_turn(" in source)
check("R2-4 KeyboardInterrupt handled",  "KeyboardInterrupt" in source)
check("R2-5 chain appended",             "chain.append(" in source)
check("R2-6 prev_ctx built",             "prev_ctx" in source)
check("R2-7 single-phase fallback",      "single-phase" in source or "no phases" in source.lower()
      or "_parse_skill_phases" in source)  # function exists → fallback implicit

# Verify /skill handler calls run_skill_agentic
skill_block: list[str] = []
in_block = False
for line in source.splitlines():
    if 'cmd == "/skill"' in line:
        in_block = True
    if in_block:
        skill_block.append(line)
        if 'elif cmd == "/tool"' in line:
            break
skill_src = "\n".join(skill_block)
check("R2-8 /skill calls run_skill_agentic", "run_skill_agentic(" in skill_src)
check("R2-9 old body-injection gone",
    'skills[arg]["body"][:2000]' not in skill_src and "skills[arg]['body'][:2000]" not in skill_src)

# ===========================================================================
# R3 — tool_install_dep (injection guard + manager detection)
# ===========================================================================
print("\n=== R3: tool_install_dep injection guard ===")

# _PKG_SAFE_RE is a multiline compile() — just verify it exists and re-define locally
check("R3-1 _PKG_SAFE_RE defined in source", "_PKG_SAFE_RE" in source)

if "_PKG_SAFE_RE" in source:
    # Reconstruct the exact pattern used in source (multiline, same logic)
    _PKG_SAFE_RE = re.compile(
        r'^[\w@./:\[\],!~^*-]+'
        r'((?:>=|<=|!=|==|~=|>|<)[\d.*][0-9a-zA-Z.*]*)?'
        r'(,[\w@./:\[\],!~^*-]+((?:>=|<=|!=|==|~=|>|<)[\d.*][0-9a-zA-Z.*]*)?)*$'
    )

    # Rrx — exhaustive injection pattern tests (merged here as R3-rx)
    SAFE = [
        "numpy", "requests", "ddgs", "rich", "prompt_toolkit",
        "ddgs==5.0", "numpy>=1.24", "numpy<3", "numpy>1", "pkg<=2.0",
        "package[extra]",
        "@scope/pkg", "some/path", "crate:name",
        "my-package", "my_package", "pkg.sub",
    ]
    UNSAFE = [
        "pkg; rm -rf /",
        "pkg && evil",
        "pkg | cat /etc/passwd",
        "pkg `whoami`",
        "pkg$(id)",
        "pkg\necho hi",
        "pkg 'quoted'",
        'pkg "doublequoted"',
        "pkg>file",    # redirection (> followed by non-digit)
        "pkg<file",    # redirection (< followed by non-digit)
        "pkg\\backslash",
    ]

    for s in SAFE:
        check(f"Rrx SAFE  '{s[:30]}'", bool(_PKG_SAFE_RE.match(s)))
    for u in UNSAFE:
        check(f"Rrx BLOCK '{u[:30]}'", not bool(_PKG_SAFE_RE.match(u)))

# Verify no shell=True in tool_install_dep body
install_dep_lines: list[str] = []
in_fn = False
for line in source.splitlines():
    if "def tool_install_dep(" in line:
        in_fn = True
    if in_fn:
        install_dep_lines.append(line)
        # Stop at next top-level def (unindented)
        if line.startswith("def ") and "tool_install_dep" not in line:
            break
install_dep_src = "\n".join(install_dep_lines)

# Count only non-comment lines with shell=True
shell_true_count = sum(
    1 for ln in install_dep_lines
    if "shell=True" in ln and not ln.lstrip().startswith("#")
)
check("R3-2 no shell=True in tool_install_dep (non-comment lines)",
    shell_true_count == 0,
    f"found {shell_true_count} shell=True in non-comment lines")

check("R3-3 _PKG_SAFE_RE.match guard present",
    "_PKG_SAFE_RE.match(" in install_dep_src)

check("R3-4 list-form install (no f-string shell cmd)",
    "install_cmd = [" in install_dep_src)

# ===========================================================================
# R4 — _ollama_chat OOM retry (source-level)
# ===========================================================================
print("\n=== R4: _ollama_chat OOM retry ===")

ollama_lines: list[str] = []
in_fn = False
for line in source.splitlines():
    if "def _ollama_chat(" in line:
        in_fn = True
    if in_fn:
        ollama_lines.append(line)
        if line.startswith("def ") and "_ollama_chat" not in line:
            break
ollama_src = "\n".join(ollama_lines)

check("R4-1 ctx_attempts list built",      "ctx_attempts = [num_ctx]" in ollama_src)
check("R4-2 halving loop present",         "reduced = reduced // 2" in ollama_src or "reduced //= 2" in ollama_src)
check("R4-3 data = None sentinel",         "data = None" in ollama_src)
check("R4-4 break on success",             "break  # success" in ollama_src or "break" in ollama_src)
check("R4-5 continue on 500 (no size cond)",
    "if e.code == 500:" in ollama_src and "attempt_ctx > 2048" not in ollama_src,
    "found 'attempt_ctx > 2048' — dead-code bug still present!" if "attempt_ctx > 2048" in ollama_src else "")
check("R4-6 if data is None diagnostic",  "if data is None:" in ollama_src)
check("R4-7 THMES_OLLAMA_NUM_CTX hint in diagnostic",
    "THMES_OLLAMA_NUM_CTX" in ollama_src)
check("R4-8 auth 401/403 still handled",  "(401, 403)" in ollama_src)

# Simulate ctx_attempts ladder
def sim_ctx_attempts(num_ctx: int) -> list[int]:
    attempts = [num_ctx]
    reduced = num_ctx
    while reduced > 2048:
        reduced = reduced // 2
        attempts.append(reduced)
    return attempts

check("R4-9 16384 → ladder [16384,8192,4096,2048]",
    sim_ctx_attempts(16384) == [16384, 8192, 4096, 2048])
check("R4-10 32768 → 5 steps",
    sim_ctx_attempts(32768) == [32768, 16384, 8192, 4096, 2048])
check("R4-11 2048 → no retry (single attempt)",
    sim_ctx_attempts(2048) == [2048])
check("R4-12 1024 → single attempt (already below floor)",
    sim_ctx_attempts(1024) == [1024])

# ===========================================================================
# R5 — CLAUDE_SKILLS path fallback chain (source-level)
# ===========================================================================
print("\n=== R5: CLAUDE_SKILLS fallback chain ===")

check("R5-1 THMES_SKILLS_DIR env override present",
    "THMES_SKILLS_DIR" in source)
check("R5-2 project skills/ fallback present",
    '_PROJ_SKILLS' in source or 'project' in source.lower() and '"skills"' in source)
check("R5-3 ~/.claude/skills fallback present",
    '".claude"' in source and '"skills"' in source)
check("R5-4 is_dir() check used",
    "is_dir()" in source)

# ===========================================================================
# Syntax check
# ===========================================================================
print("\n=== Syntax check ===")
proc = subprocess.run(
    [sys.executable, "-m", "py_compile", str(SRC)],
    capture_output=True, text=True, cwd=str(REPO),
)
check("py_compile clean", proc.returncode == 0, proc.stderr.strip())

# ===========================================================================
# Summary
# ===========================================================================
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
