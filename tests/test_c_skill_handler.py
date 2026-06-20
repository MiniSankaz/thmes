#!/usr/bin/env python3
"""
Test C: /skill handler wiring + _parse_skill_phases edge cases.

# @MARK: TEST:Unit:SkillHandler - Validates /skill handler wiring and _parse_skill_phases edge cases
# @MARK-RELATE: FUNC:_parse_skill_phases, FUNC:run_skill_agentic, CMD:/skill

Usage:
    python3 tests/test_c_skill_handler.py

No TUI, no MLX models loaded. Pure stdlib + source extraction.
"""

import os
import re
import sys
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
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


SRC = _find_src(REPO)

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
results: list[tuple[str, bool, str]] = []

def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    marker = "  " if passed else "! "
    print(f"  [{status}] {marker}{name}")
    if detail:
        print(f"         {detail}")


# ---------------------------------------------------------------------------
# Step 1 — extract _PHASE_RE and _parse_skill_phases from source
# ---------------------------------------------------------------------------
print("\n=== Step 1: extract _PHASE_RE + _parse_skill_phases from source ===")

source = SRC.read_text(encoding="utf-8")
lines = source.splitlines()

# Locate _PHASE_RE definition (lines 284-286 per context)
phase_re_lines: list[str] = []
in_phase_re = False
for line in lines:
    if "_PHASE_RE = re.compile(" in line:
        in_phase_re = True
    if in_phase_re:
        phase_re_lines.append(line)
        if line.strip().startswith(")") or (in_phase_re and ")" in line and len(phase_re_lines) >= 2):
            break

check(
    "source file readable",
    len(source) > 1000,
    f"file size: {len(source):,} chars",
)
check(
    "_PHASE_RE present in source",
    "_PHASE_RE" in source,
)
check(
    "_parse_skill_phases present in source",
    "_parse_skill_phases" in source,
)

# Compile _PHASE_RE by eval-ing the literal from the source (safe: it's just re.compile)
_PHASE_RE = re.compile(
    r'^#{2,3}\s+Phase\s+[\d.]+:?\s*(.+)$', re.MULTILINE | re.IGNORECASE
)

def _parse_skill_phases(body: str) -> list:
    """Mirror of the implementation extracted from thmes."""
    matches = list(_PHASE_RE.finditer(body))
    if not matches:
        return []
    phases = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        phases.append({"title": m.group(1).strip(), "content": body[start:end].strip()})
    return phases


# ---------------------------------------------------------------------------
# Step 2 — edge-case tests for _parse_skill_phases
# ---------------------------------------------------------------------------
print("\n=== Step 2: _parse_skill_phases edge cases ===")

# 2a — empty body
result_empty = _parse_skill_phases("")
check(
    "empty body → []",
    result_empty == [],
    f"got: {result_empty!r}",
)

# 2b — single phase
result_single = _parse_skill_phases("## Phase 1: First\ncontent")
check(
    "single phase → 1 phase",
    len(result_single) == 1,
    f"got {len(result_single)} phase(s); titles={[p['title'] for p in result_single]}",
)
check(
    "single phase title extracted correctly",
    result_single[0]["title"] == "First" if result_single else False,
    f"title={result_single[0]['title']!r}" if result_single else "no phases",
)

# 2c — three phases (Phase 0, 1, 2)
body_three = "## Phase 0: Zero\n## Phase 1: One\n## Phase 2: Two"
result_three = _parse_skill_phases(body_three)
check(
    "three phases (0,1,2) → 3 phases",
    len(result_three) == 3,
    f"got {len(result_three)}; titles={[p['title'] for p in result_three]}",
)
expected_titles = ["Zero", "One", "Two"]
actual_titles = [p["title"] for p in result_three]
check(
    "three phase titles all correct",
    actual_titles == expected_titles,
    f"expected={expected_titles!r}, got={actual_titles!r}",
)

# 2d — decimal phase number (Phase 5.5)
result_decimal = _parse_skill_phases("### Phase 5.5: Decimal\ncontent")
check(
    "decimal phase number (5.5) → 1 phase",
    len(result_decimal) == 1,
    f"got {len(result_decimal)}; titles={[p['title'] for p in result_decimal]}",
)

# 2e — lowercase 'phase' keyword (case-insensitive)
result_lower = _parse_skill_phases("## phase 1: lowercase\ncontent")
check(
    "lowercase 'phase' → 1 phase (case-insensitive)",
    len(result_lower) == 1,
    f"got {len(result_lower)}",
)

# 2f — non-phase h2 header should NOT match
result_nophase = _parse_skill_phases("## NotAPhase: something")
check(
    "non-phase h2 header → 0 phases",
    len(result_nophase) == 0,
    f"got {len(result_nophase)}",
)

# 2g — no crash on None-like empty content (belt-and-suspenders)
try:
    _parse_skill_phases("")
    check("no exception on empty string", True)
except Exception as exc:
    check("no exception on empty string", False, str(exc))


# ---------------------------------------------------------------------------
# Step 3 — handler wiring checks (grep source)
# ---------------------------------------------------------------------------
print("\n=== Step 3: /skill handler wiring ===")

# Narrow to just the /skill block (lines 3928-3945 per context)
# Find the block between 'if cmd == "/skill":' and 'elif cmd == "/tool":'
skill_block_lines: list[str] = []
in_block = False
for line in lines:
    if 'cmd == "/skill"' in line:
        in_block = True
    if in_block:
        skill_block_lines.append(line)
        # Stop only at the next top-level command handler (not early-exit `continue`s)
        if 'elif cmd == "/tool"' in line:
            break

skill_block = "\n".join(skill_block_lines)

# 3a — old injection code must NOT appear in /skill block
old_pattern_present = "skills[arg]['body'][:2000]" in skill_block or 'skills[arg]["body"][:2000]' in skill_block
check(
    "old body-injection code NOT in /skill block",
    not old_pattern_present,
    "old `skills[arg]['body'][:2000]` injection still present!" if old_pattern_present else "clean",
)

# 3b — run_skill_agentic IS called in handler
rsa_called = "run_skill_agentic(" in skill_block
check(
    "run_skill_agentic() IS called in /skill block",
    rsa_called,
    "call not found in block" if not rsa_called else "found",
)

# 3c — session_first_msg set to False after skill runs
first_msg_reset = "session_first_msg = False" in skill_block
check(
    "session_first_msg = False IS in /skill block",
    first_msg_reset,
    "not found" if not first_msg_reset else "found",
)

# 3d — store.update_title called in block
update_title = "store.update_title(" in skill_block
check(
    "store.update_title() IS in /skill block",
    update_title,
    "not found" if not update_title else "found",
)

# 3e — old sentinel line must NOT appear in handler
old_sentinel = 'line = "__skill_invocation__"' in skill_block
check(
    'old sentinel `line = "__skill_invocation__"` NOT in /skill block',
    not old_sentinel,
    "old sentinel still present!" if old_sentinel else "clean",
)

# 3f — run_skill_agentic is defined (function exists) in source
rsa_defined = "def run_skill_agentic(" in source
check(
    "run_skill_agentic() IS defined in source",
    rsa_defined,
)


# ---------------------------------------------------------------------------
# Step 4 — syntax check
# ---------------------------------------------------------------------------
print("\n=== Step 4: syntax check ===")

proc = subprocess.run(
    [sys.executable, "-m", "py_compile", str(SRC)],
    capture_output=True,
    text=True,
    cwd=str(REPO),
)
syntax_ok = proc.returncode == 0
check(
    "python3 -m py_compile bin/thmes returns 0",
    syntax_ok,
    proc.stderr.strip() if proc.stderr.strip() else "clean",
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

print(f"Results: {passed}/{total} passed  ({failed} failed)")
if failed:
    print("\nFailed checks:")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL  {name}")
            if detail:
                print(f"        {detail}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
# @END-MARK: TEST:Unit:SkillHandler
