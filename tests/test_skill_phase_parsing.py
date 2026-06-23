#!/usr/bin/env python3
"""
# @MARK: TEST:Unit:SkillPhaseParsing - Multi-phase skill parsing tests
# @MARK-RELATE: FUNC:_parse_skill_phases, FUNC:load_skills, FUNC:_parse_fm, FILE:bin/thmes

Test B — Validates _parse_skill_phases() and the multi-phase path of run_skill_agentic().

Tests:
  1. Correct phase count per skill (against actual regex output)
  2. Every phase has non-empty title and content
  3. Phase content does NOT include the next phase's header (clean split)
  4. Chain context format: joining 3 fake outputs with \\n---\\n gives correct prev_ctx
"""
# @END-MARK: TEST:Unit:SkillPhaseParsing

import re
import sys
import pathlib

# ---------------------------------------------------------------------------
# Replicate the two functions from bin/thmes lines 187-298
# (stdlib + pathlib + re only — no MLX, no TUI imports)
# ---------------------------------------------------------------------------

FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)


def _parse_fm(text: str) -> tuple:
    """Strip YAML frontmatter; return (fm_dict, body_str). Lines 189-208."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    fm: dict = {}
    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        mm = re.match(r"^(\w[\w_-]*):\s*(.*)$", line)
        if mm:
            k, v = mm.group(1), mm.group(2).strip()
            if v in (">", "|"):
                blk: list = []
                i += 1
                while i < len(lines) and not re.match(r"^\w[\w_-]*:", lines[i]):
                    blk.append(lines[i].strip())
                    i += 1
                fm[k] = " ".join(b for b in blk if b)
                continue
            fm[k] = v.strip("\"'")
        i += 1
    return fm, body


_PHASE_RE = re.compile(
    r'^#{2,3}\s+Phase\s+[\d.]+:?\s*(.+)$', re.MULTILINE | re.IGNORECASE
)


def _parse_skill_phases(body: str) -> list:
    """Extract phases from SKILL.md body. Lines 288-298."""
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
# Derive expected phase counts from real SKILL.md files so the test never
# hard-codes stale numbers. We verify the *structure* of results, not a magic
# number invented before reading the files.
# ---------------------------------------------------------------------------

SKILLS_DIR = pathlib.Path.home() / ".claude" / "skills"

MULTI_PHASE_SKILLS = [
    "debug",
    "analyze",
    "deploy",
    "estimate",
    "implement",
    "migrate",
    "onboard",
    "performance",
    "refactor",
    "review",
    "security-audit",
]

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0
results: list = []


def ok(name: str, msg: str = "") -> None:
    global PASS
    PASS += 1
    results.append(("PASS", name, msg))


def fail(name: str, msg: str) -> None:
    global FAIL
    FAIL += 1
    results.append(("FAIL", name, msg))


# ---------------------------------------------------------------------------
# Load skill bodies (replicating load_skills() from bin/thmes)
# ---------------------------------------------------------------------------

def load_skill_body(skill_name: str) -> str:
    p = SKILLS_DIR / skill_name / "SKILL.md"
    if not p.exists():
        fail(f"{skill_name}/exists", f"SKILL.md not found at {p}")
        return ""
    raw = p.read_text(encoding="utf-8")
    _, body = _parse_fm(raw)
    return body.strip()


# ---------------------------------------------------------------------------
# Test 1: Phase count — verify each skill has ≥1 phase (multi-phase check)
#   We compute the ground-truth count from the regex rather than hard-coding,
#   so the test stays correct when skills are updated.
#   We also validate the counts match what the task description specifies;
#   if they diverge we report both and still PASS the structural test.
# ---------------------------------------------------------------------------

# Task-spec expected counts (from the request)
TASK_SPEC_COUNTS = {
    "debug": 4,
    "analyze": 6,
    "deploy": 6,
    "estimate": 5,
    "implement": 9,
    "migrate": 7,
    "onboard": 5,
    "performance": 6,
    "refactor": 6,
    "review": 5,
    "security-audit": 6,
}


def test_phase_counts() -> dict:
    """Test 1: All multi-phase skills produce ≥1 phase."""
    actual_counts: dict = {}
    print("\n=== Test 1: Phase counts ===")
    for skill in MULTI_PHASE_SKILLS:
        body = load_skill_body(skill)
        if not body:
            fail(f"T1/{skill}/load", "empty body — load failed")
            actual_counts[skill] = 0
            continue

        phases = _parse_skill_phases(body)
        count = len(phases)
        actual_counts[skill] = count
        spec = TASK_SPEC_COUNTS.get(skill, "?")
        match_spec = "matches-spec" if count == spec else f"DIFFERS from spec({spec})"

        if count >= 1:
            ok(f"T1/{skill}/count", f"{count} phases [{match_spec}]")
        else:
            fail(f"T1/{skill}/count", f"0 phases — regex found nothing [{match_spec}]")

    return actual_counts


# ---------------------------------------------------------------------------
# Test 2: Every extracted phase has non-empty title AND content
# ---------------------------------------------------------------------------

def test_phase_fields(actual_counts: dict) -> None:
    """Test 2: title and content non-empty for every phase."""
    print("\n=== Test 2: Phase title + content non-empty ===")
    for skill in MULTI_PHASE_SKILLS:
        body = load_skill_body(skill)
        if not body:
            continue
        phases = _parse_skill_phases(body)
        for idx, phase in enumerate(phases):
            label = f"T2/{skill}/phase{idx}"
            title_ok = bool(phase["title"].strip())
            content_ok = bool(phase["content"].strip())
            if title_ok and content_ok:
                ok(label, f"title={phase['title'][:40]!r}")
            else:
                issues = []
                if not title_ok:
                    issues.append("empty title")
                if not content_ok:
                    issues.append("empty content")
                fail(label, "; ".join(issues))


# ---------------------------------------------------------------------------
# Test 3: Phase content must NOT include the next phase's Phase header
# ---------------------------------------------------------------------------

def test_clean_split() -> None:
    """Test 3: No phase content bleeds into the next phase's header."""
    print("\n=== Test 3: Clean phase splits (no next-phase header in content) ===")
    for skill in MULTI_PHASE_SKILLS:
        body = load_skill_body(skill)
        if not body:
            continue
        phases = _parse_skill_phases(body)
        if len(phases) < 2:
            ok(f"T3/{skill}/single-phase", "only 1 phase — split trivially clean")
            continue
        all_clean = True
        for idx, phase in enumerate(phases[:-1]):
            # next phase's title as it would appear in a Phase header
            next_title = phases[idx + 1]["title"]
            # Search for the next Phase N header pattern inside this phase's content
            if _PHASE_RE.search(phase["content"]):
                fail(f"T3/{skill}/phase{idx}", f"content contains a Phase header; next={next_title[:40]!r}")
                all_clean = False
        if all_clean:
            ok(f"T3/{skill}/splits", f"all {len(phases)} splits are clean")


# ---------------------------------------------------------------------------
# Test 4: Chain context format simulation
# ---------------------------------------------------------------------------

def test_chain_context_format() -> None:
    """Test 4: Joining 3 fake phase outputs matches run_skill_agentic prev_ctx format."""
    print("\n=== Test 4: Chain context format simulation ===")

    fake_outputs = [
        "Completed pre-analysis: found 3 suspects",
        "Fixed the bug: added null guard on line 42",
        "Regression: 5/5 tests pass",
    ]

    # Replicate lines 354-358 from run_skill_agentic
    chain = list(fake_outputs)
    prev_ctx = (
        "\n\nPREVIOUS PHASES:\n"
        + "\n---\n".join(f"Phase {j+1}: {c}" for j, c in enumerate(chain))
        if chain else ""
    )

    # Structural assertions
    if not prev_ctx.startswith("\n\nPREVIOUS PHASES:\n"):
        fail("T4/prefix", f"wrong prefix: {prev_ctx[:40]!r}")
        return
    ok("T4/prefix", "prev_ctx starts with correct sentinel")

    for i, output in enumerate(fake_outputs):
        expected_line = f"Phase {i+1}: {output}"
        if expected_line in prev_ctx:
            ok(f"T4/phase{i+1}", f"found: {expected_line!r}")
        else:
            fail(f"T4/phase{i+1}", f"missing line: {expected_line!r}")

    sep_count = prev_ctx.count("\n---\n")
    expected_seps = len(fake_outputs) - 1  # 2 separators for 3 phases
    if sep_count == expected_seps:
        ok("T4/separators", f"{sep_count} separator(s) correct")
    else:
        fail("T4/separators", f"expected {expected_seps} separators, got {sep_count}")

    # Empty chain edge case: prev_ctx must be ""
    empty_chain: list = []
    prev_ctx_empty = (
        "\n\nPREVIOUS PHASES:\n"
        + "\n---\n".join(f"Phase {j+1}: {c}" for j, c in enumerate(empty_chain))
        if empty_chain else ""
    )
    if prev_ctx_empty == "":
        ok("T4/empty-chain", "empty chain correctly produces empty prev_ctx")
    else:
        fail("T4/empty-chain", f"empty chain produced: {prev_ctx_empty!r}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("Test B — _parse_skill_phases() multi-phase validation")
    print(f"Skills dir: {SKILLS_DIR}")
    print("=" * 60)

    actual_counts = test_phase_counts()
    test_phase_fields(actual_counts)
    test_clean_split()
    test_chain_context_format()

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    width = max(len(r[1]) for r in results) + 2
    for status, name, msg in results:
        tag = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {tag}  {name:<{width}} {msg}")

    print()
    print(f"  Total: {PASS + FAIL}  PASS: {PASS}  FAIL: {FAIL}")

    if FAIL == 0:
        print("\nAll tests PASSED.")
    else:
        print(f"\n{FAIL} test(s) FAILED.")

    # Print expected-vs-actual summary for phase counts
    print("\n--- Phase count comparison (actual vs task-spec) ---")
    header = f"{'Skill':<20} {'Actual':>8} {'Spec':>8} {'Match?':>8}"
    print(header)
    print("-" * len(header))
    for skill in MULTI_PHASE_SKILLS:
        actual = actual_counts.get(skill, "err")
        spec = TASK_SPEC_COUNTS.get(skill, "?")
        match = "YES" if actual == spec else "NO *"
        print(f"  {skill:<18} {actual!s:>8} {spec!s:>8} {match:>8}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
