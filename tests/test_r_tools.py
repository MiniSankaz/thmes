#!/usr/bin/env python3
"""
Regression tests for the mutating / ask-risk tools — functions are EXECUTED
against a /tmp sandbox and asserted on REAL filesystem + stdout effects
(no model, no network).

Rt1 : write_file   — create (w), append (a), byte-count return
Rt2 : edit_file    — replace first match; error on missing str / missing file
Rt3 : delete_file  — remove file; refuse a directory
Rt4 : bash         — capture stdout; real side effect; nonzero exit no-crash
Rt5 : python       — run safe code; sandbox BLOCKS unsafe import (os/sys)
Rt6 : read/list/grep
Rt7 : security     — _validate_user_path blocks another user's home (write+delete)

Usage:
    python3 tests/test_r_tools.py
    THMES_BIN=bin/thmes python3 tests/test_r_tools.py
"""
import importlib.machinery
import importlib.util
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _find_src(repo: Path) -> Path:
    override = os.environ.get("THMES_BIN")
    if override:
        p = Path(override)
        return p if p.is_absolute() else (repo / p)
    for name in ("thmes",):
        p = repo / "bin" / name
        if p.exists():
            return p
    return repo / "bin" / "thmes"


SRC = _find_src(REPO)

# Load the whole module (tool fns only touch stdlib — Path/subprocess) so we
# can EXECUTE them, not grep source.
_loader = importlib.machinery.SourceFileLoader("thmes_under_test", str(SRC))
_spec = importlib.util.spec_from_loader("thmes_under_test", _loader)
T = importlib.util.module_from_spec(_spec)
sys.modules["thmes_under_test"] = T
_loader.exec_module(T)

results: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    flag = "  " if ok else "! "
    print(f"  [{status}] {flag}{name}")
    if detail and not ok:
        print(f"         → {detail}")


SB = Path("/tmp/thmes-toolqa-regress")
shutil.rmtree(SB, ignore_errors=True)
SB.mkdir(parents=True)

# ===========================================================================
print("\n=== Rt1: write_file ===")
f = SB / "a.py"
r = T.tool_write_file(str(f), "print('hello thmes')\n")
check("Rt1-1 write creates file", f.exists())
check("Rt1-2 write content exact", f.read_text() == "print('hello thmes')\n")
check("Rt1-3 write return has byte count", "wrote" in r and "bytes" in r, r)
r = T.tool_write_file(str(f), "# tail\n", mode="a")
check("Rt1-4 append adds, does not truncate", f.read_text().endswith("# tail\n")
      and "hello thmes" in f.read_text())
check("Rt1-5 append return says appended", "appended" in r, r)

# ===========================================================================
print("\n=== Rt2: edit_file ===")
r = T.tool_edit_file(str(f), "hello thmes", "hi thmes")
check("Rt2-1 replaces first match", "hi thmes" in f.read_text()
      and "hello thmes" not in f.read_text())
check("Rt2-2 return confirms", "edited" in r, r)
r = T.tool_edit_file(str(f), "NOPE_NOT_PRESENT", "x")
check("Rt2-3 missing old_str → graceful error", r.startswith("Error")
      and "not found" in r, r)
r = T.tool_edit_file(str(SB / "ghost.py"), "a", "b")
check("Rt2-4 missing file → graceful error", r.startswith("Error")
      and "does not exist" in r, r)

# ===========================================================================
print("\n=== Rt3: delete_file ===")
r = T.tool_delete_file(str(f))
check("Rt3-1 removes file", not f.exists())
check("Rt3-2 return confirms", "delete" in r.lower() or "removed" in r.lower(), r)
r = T.tool_delete_file(str(SB))
check("Rt3-3 refuses a directory", r.startswith("Error") and "director" in r.lower(), r)

# ===========================================================================
print("\n=== Rt4: bash ===")
r = T.tool_bash("echo hello-from-bash")
check("Rt4-1 captures stdout", "hello-from-bash" in r, r)
side = SB / "b.txt"
T.tool_bash(f"echo written-by-bash > {side}")
check("Rt4-2 real side effect (file written)", side.exists()
      and "written-by-bash" in side.read_text())
r = T.tool_bash("ls /definitely/not/here/xyz 2>&1")
check("Rt4-3 nonzero exit returns output (no crash)", isinstance(r, str) and len(r) > 0)
# backgrounded command (trailing &): must return FAST (no 30s pipe hang on the
# detached child) and the process must actually run. Regression for the server-
# start pattern that used to block tool_bash for the full timeout.
import time as _time
bgf = SB / "bg.txt"
_t0 = _time.time()
r = T.tool_bash(f"(sleep 0.3; echo bg-done > {bgf}) &")
_dt = _time.time() - _t0
check("Rt4-4 background returns fast (<5s, not 30s)", _dt < 5, f"took {_dt:.1f}s")
check("Rt4-5 background reports 'detached/background'", "background" in r.lower(), r[:80])
for _ in range(40):
    if bgf.exists(): break
    _time.sleep(0.1)
check("Rt4-6 background process actually ran", bgf.exists() and "bg-done" in bgf.read_text())

# ===========================================================================
print("\n=== Rt5: python (sandboxed) ===")
r = T.tool_python("print(6*7)")
check("Rt5-1 returns stdout", "42" in r, r)
r = T.tool_python("import math; print(math.sqrt(16))")
check("Rt5-2 allows safe module (math)", "4.0" in r, r)
r = T.tool_python("import os; os.system('echo pwned')")
check("Rt5-3 sandbox BLOCKS unsafe import (os)", "blocked by sandbox" in r, r)

# ===========================================================================
print("\n=== Rt6: read / list / grep ===")
g = SB / "c.txt"
g.write_text("alpha\nNEEDLE_X\nbeta\n")
check("Rt6-1 read returns content", "NEEDLE_X" in T.tool_read_file(str(g)))
check("Rt6-2 list_dir lists entries", "c.txt" in T.tool_list_dir(str(SB)))
check("Rt6-3 grep finds pattern", "NEEDLE_X" in T.tool_grep("NEEDLE_X", str(g)))

# ===========================================================================
print("\n=== Rt7: security — cross-user-home guard ===")
evil = "/Users/someoneelse/evil.txt"
r = T.tool_write_file(evil, "x")
check("Rt7-1 write blocks other user's home", r.startswith("Error")
      and "refus" in r.lower(), r)
check("Rt7-2 ...and did NOT create it", not Path(evil).exists())
r = T.tool_delete_file("/Users/someoneelse/whatever.txt")
check("Rt7-3 delete blocks other user's home", r.startswith("Error"), r)

# ===========================================================================
print("\n=== Rt8: make_report (built-in report tool, stdlib-only) ===")
import glob as _glob
htmlout = T._md_to_html("## Head\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- x\n\n> note\n\n```\ncode\n```")
check("Rt8-1 md→html heading", "<h2>" in htmlout)
check("Rt8-2 md→html table", "<table>" in htmlout and "<th>A</th>" in htmlout)
check("Rt8-3 md→html list", "<ul>" in htmlout and "<li>x</li>" in htmlout)
check("Rt8-4 md→html blockquote", "<blockquote>" in htmlout)
check("Rt8-5 md→html code fence", "pre class='term'" in htmlout)
check("Rt8-6 inline bold + HTML-escape", "<strong>b</strong>" in T._md_inline("**b**")
      and "&lt;x&gt;" in T._md_inline("<x>"))
T.THMES_HOME = SB                      # redirect reports dir into the sandbox
r = T.tool_make_report("QA Report", "## Hi\n\nbody **bold**", "html")
htmls = _glob.glob(str(SB / "reports" / "*.html"))
check("Rt8-7 html report file created", len(htmls) == 1 and "report written" in r)
rc = Path(htmls[0]).read_text() if htmls else ""
check("Rt8-8 report has title + body + css", "QA Report" in rc
      and "<strong>bold</strong>" in rc and ".rhead" in rc)
T.tool_make_report("MD One", "plain body", "md")
check("Rt8-9 md format writes a .md file", _glob.glob(str(SB / "reports" / "*.md")) != [])

shutil.rmtree(SB, ignore_errors=True)
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print("\n" + "=" * 60)
print(f"Total: {total}  PASS: {passed}  FAIL: {failed}")
print("=" * 60)
sys.exit(1 if failed else 0)
