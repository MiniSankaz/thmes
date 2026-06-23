#!/usr/bin/env python3
"""
E2E test — launches thmes in a real tmux session and drives it like a human.

Strategy  : tmux new-session → send-keys → capture-pane (plain text)
Model     : ol:gemma4:e4b via Ollama (localhost:11434)
No mocks  : everything is the real app, real Ollama, real Rich/prompt_toolkit

E1  startup         — TUI comes up and responds to input
E2  /help           — "commands" panel lists slash commands
E3  /skill list     — lists skills from project skills/ dir
E4  /model          — "models (" panel with Ollama entries
E5  /sessions       — "sessions (" panel with current session
E6  /breakers       — circuit-breaker status shows
E7  bad command     — "unknown command:" + "try /help" hint
E8  send message    — Ollama generates a real reply  (skipped if Ollama down)
F1  write_file      — model calls write_file, file appears on disk  (skipped if Ollama down)
F2  edit_file       — model calls edit_file, content updated on disk (skipped if Ollama down)
F3  delete_file     — model calls delete_file, file removed from disk (skipped if Ollama down)
E9  /quit           — prints "bye", process exits

Usage:
    python3 tests/test_e2e_tui.py
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

REPO      = Path(__file__).resolve().parent.parent
SESSION   = "thmes_e2e"
_TEST_FILE = "/tmp/thmes_e2e_tool_test.txt"


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

# ── Result tracking ───────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []

def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    flag   = "  " if ok else "! "
    print(f"  [{status}] {flag}{name}")
    if detail and not ok:
        print(f"         → {detail}")

def skip(name: str, reason: str) -> None:
    results.append((name, True, f"SKIP: {reason}"))
    print(f"  [SKIP]   {name} — {reason}")

# ── tmux helpers ─────────────────────────────────────────────────────────
def _tmux(*args: str) -> tuple[str, int]:
    r = subprocess.run(["tmux"] + list(args), capture_output=True, text=True)
    return r.stdout, r.returncode

def capture(scrollback: int = 200) -> str:
    """Grab pane content including last *scrollback* lines of history."""
    out, _ = _tmux("capture-pane", "-t", SESSION, "-p", "-J",
                   "-S", f"-{scrollback}")
    return out

def send(text: str, *, enter: bool = True) -> None:
    keys = [text, "Enter"] if enter else [text]
    _tmux("send-keys", "-t", SESSION, *keys)

def wait_for(text: str, timeout: float = 10.0) -> bool:
    """Poll until *text* appears in the pane (or timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if text in capture():
            return True
        time.sleep(0.25)
    return False

def wait_for_change(baseline: str, timeout: float = 60.0) -> str:
    """Return updated pane content once it differs from *baseline*."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = capture()
        if current != baseline:
            return current
        time.sleep(0.3)
    return capture()

def wait_for_prompt(heartbeat: float = 30.0) -> bool:
    """Wait until model finishes — heartbeat-based, no fixed timeout.

    Strategy: pane content stops changing for 2 s AND the input prompt
    is visible AND the routing spinner is gone.  The routing spinner
    runs AFTER model output and may pause between frames, causing a
    false 2-s stability window — so we must also gate on "routing" absent.

    Times out only when the pane has been completely static for `heartbeat`
    seconds without reaching the ready state — meaning the model is truly
    stuck (crashed, hung, or errored), not just slow.
    """
    prev        = ""
    stable_for  = 0.0
    STABLE_NEED = 2.0

    while True:
        visible = capture(scrollback=0)
        if visible == prev:
            stable_for += 0.5
            if stable_for >= STABLE_NEED:
                # Stable for 2 s, prompt present, router not spinning
                if "you" in visible and "routing" not in visible:
                    return True
                # Still routing — keep waiting
            if stable_for >= heartbeat:
                # No pane activity for heartbeat seconds — model stuck
                return False
        else:
            stable_for = 0.0
            prev = visible
        time.sleep(0.5)

def wait_for_prompt_with_approval(heartbeat: float = 30.0) -> bool:
    """Like wait_for_prompt but also auto-approves tool/salvage prompts as they appear.

    Uses heartbeat detection — returns as soon as model is done regardless of
    how long it took, and only times out when the pane is static for `heartbeat`
    seconds without reaching the ready state.
    """
    prev       = ""
    stable_for = 0.0
    STABLE_NEED = 2.0

    while True:
        visible = capture(scrollback=0)
        # Auto-approve tool execution and salvage-write prompts
        if "approve?" in visible or "write this file?" in visible:
            send("y", enter=True)
            stable_for = 0.0
            time.sleep(0.5)
            continue
        # Decline topic-change "new session?" prompt — stay in current session
        if "session ใหม่ไหม?" in visible:
            send("n", enter=True)
            stable_for = 0.0
            time.sleep(0.5)
            continue
        if visible == prev:
            stable_for += 0.5
            if stable_for >= STABLE_NEED:
                if "you" in visible and "routing" not in visible:
                    return True
            if stable_for >= heartbeat:
                return False
        else:
            stable_for = 0.0
            prev = visible
        time.sleep(0.5)
    return False

def kill_session() -> None:
    _tmux("kill-session", "-t", SESSION)

# ── Prerequisite checks ───────────────────────────────────────────────────
print("\n=== Prerequisites ===")

_WRAPPER_NAMES   = ("dev-thmes",)   # this DEV checkout installs under the dev- prefix
_VENV_CANDIDATES = ("~/.thmes-env", "~/.mlx-env")

has_tmux    = shutil.which("tmux") is not None
has_wrapper = any(Path(os.path.expanduser(f"~/.local/bin/{n}")).exists()
                  for n in _WRAPPER_NAMES)
has_venv    = any(Path(os.path.expanduser(f"{v}/bin/python")).exists()
                  for v in _VENV_CANDIDATES)
skills_dir  = REPO / "skills"

check("tmux available",          has_tmux,    "install tmux first")
check("dev-thmes wrapper", has_wrapper, "run ./install.sh first")
check("python venv",             has_venv,    "run setup-mac.sh first")

if not (has_tmux and (has_wrapper or has_venv)):
    print("\nMissing prerequisites — cannot run E2E tests.")
    sys.exit(1)

# Check Ollama
try:
    r = subprocess.run(
        ["curl", "-sf", "http://localhost:11434/api/tags"],
        capture_output=True, text=True, timeout=3,
    )
    import json as _json
    _models = [m["name"] for m in _json.loads(r.stdout).get("models", [])]
    ollama_ok = "gemma4:e4b" in _models
    check("Ollama + gemma4:e4b", ollama_ok,
          f"available models: {_models[:5]}" if not ollama_ok else "")
except Exception as e:
    ollama_ok = False
    check("Ollama + gemma4:e4b", False, str(e))

# ── Determine launch command ──────────────────────────────────────────────
# THMES_BIN overrides everything — lets us e2e a specific checkout even when an
# installed wrapper exists.
_py = next(
    (os.path.expanduser(f"{v}/bin/python") for v in _VENV_CANDIDATES
     if Path(os.path.expanduser(f"{v}/bin/python")).exists()),
    "python3"
)
if os.environ.get("THMES_BIN"):
    launch_cmd = f"THMES_MODEL=ol:gemma4:e4b {_py} {os.environ['THMES_BIN']}"
elif has_wrapper:
    for _n in _WRAPPER_NAMES:
        _w = os.path.expanduser(f"~/.local/bin/{_n}")
        if Path(_w).exists():
            # Prepend the model IN the command — tmux new-session inherits the tmux
            # *server's* env, not ours, so an exported THMES_MODEL never reaches the
            # wrapper (it would default to qwen-vl and fail on an Ollama-only box).
            launch_cmd = f"THMES_MODEL=ol:gemma4:e4b {_w}"
            break
else:
    launch_cmd = f"THMES_MODEL=ol:gemma4:e4b {_py} {_find_src(REPO)}"

# ── Run E2E suite ─────────────────────────────────────────────────────────
print(f"\n=== E2E (session: {SESSION}) ===")
print(f"Launch : {launch_cmd}")

try:
    # Clean up any leftover session
    kill_session()
    time.sleep(0.3)

    # Launch inside tmux (180 wide × 50 tall — enough for Rich panels)
    _, rc = _tmux("new-session", "-d", "-s", SESSION, "-x", "180", "-y", "50",
                  launch_cmd)
    if rc != 0:
        print(f"[FATAL] Failed to start tmux session (exit {rc})")
        sys.exit(1)

    # ── E0: Model picker bypass ───────────────────────────────────────────
    # Startup model picker (`_model_picker`) shows "model ›" before the main
    # TUI loads. Press Enter to accept the default so all E1+ tests see the
    # real TUI prompt, not the picker's "✗ enter 1–N" rejection.
    time.sleep(1.5)
    _picker_up = (wait_for("type number to pick", timeout=6) or
                  "model ›" in capture())
    if _picker_up:
        send("", enter=True)   # accept default model
        time.sleep(2.0)        # let TUI fully initialize after model load

    # ── E1: Startup ───────────────────────────────────────────────────────
    # The toolbar always shows "/help" — send /help immediately to confirm
    # the TUI is alive and accepting input.
    send("/help")
    ready = wait_for("commands", timeout=15)
    check("E1  startup — TUI alive (responds to /help)", ready,
          f"pane after 15 s:\n{capture()[-400:]}" if not ready else "")

    # ── E2: /help ─────────────────────────────────────────────────────────
    # Already triggered above; verify richer content
    pane = capture()
    has_commands_panel = "commands" in pane
    has_skill_entry    = "/skill" in pane
    has_model_entry    = "/model" in pane
    check("E2  /help — 'commands' panel title",     has_commands_panel, pane[-300:] if not has_commands_panel else "")
    check("E2  /help — '/skill' listed",            has_skill_entry,    "")
    check("E2  /help — '/model' listed",            has_model_entry,    "")

    # ── E3: /skill list ───────────────────────────────────────────────────
    send("/skill list")
    found = wait_for("skills (", timeout=6)
    pane  = capture()
    check("E3  /skill list — panel 'skills (N)' appears", found,
          pane[-300:] if not found else "")
    # Verify skill count > 0
    import re as _re
    m = _re.search(r"skills \((\d+)\)", pane)
    if m:
        n = int(m.group(1))
        check(f"E3  /skill list — {n} skills loaded (>0)", n > 0,
              "0 skills found — skills/ dir may be empty")
    else:
        check("E3  /skill list — skill count parseable", False, pane[-200:])

    # ── E4: /model ────────────────────────────────────────────────────────
    send("/model")
    found = wait_for("models (", timeout=6)
    pane  = capture()
    check("E4  /model — 'models (' panel appears", found, pane[-300:] if not found else "")
    if found:
        check("E4  /model — Ollama section present", "ollama" in pane.lower(), "")

    # ── E5: /session list ────────────────────────────────────────────────
    # Note: command is /session (singular), not /sessions
    send("/session list")
    found = wait_for("sessions (", timeout=6)
    pane  = capture()
    check("E5  /session list — 'sessions (N)' panel appears", found, pane[-300:] if not found else "")
    if found:
        pane5 = capture()
        # Panel title: "sessions (N)  • current: <session_id>"
        # The bullet (•) may render differently; match just "current"
        check("E5  /session list — 'current' session marker present",
              "current" in pane5, pane5[-200:])

    # ── E6: /breakers ────────────────────────────────────────────────────
    send("/breakers")
    # Either "no tool calls tracked yet" or "circuit breakers" panel
    found = wait_for("no tool calls", timeout=6) or wait_for("circuit breakers", timeout=2)
    pane  = capture()
    check("E6  /breakers — status message appears", found, pane[-200:] if not found else "")

    # ── E7: unknown command ───────────────────────────────────────────────
    send("/this_does_not_exist_xyz")
    found = wait_for("unknown command", timeout=5)
    pane  = capture()
    check("E7  bad command — 'unknown command:' shown",  found, pane[-200:] if not found else "")
    check("E7  bad command — 'try /help' hint shown",
          "try /help" in capture(), "")

    # ── E8: real message → Ollama reply ───────────────────────────────────
    if not ollama_ok:
        skip("E8  real message → Ollama reply", "Ollama not reachable")
    else:
        baseline = capture()
        send("reply with exactly one word: hi")
        # Wait for pane to change (model starts generating)
        changed = wait_for_change(baseline, timeout=10)
        # Then wait for model to finish — look for the prompt ❯ reappearing
        # (prompt_toolkit redraws input prompt after generation completes)
        # Also accept any new non-empty line after the user message
        time.sleep(2.0)
        final = capture()
        new_lines = [l for l in final.splitlines() if l.strip()
                     and l not in baseline.splitlines()]
        has_response = len(new_lines) >= 1
        check("E8  real message — model produced output",
              has_response,
              f"new lines: {new_lines[:5]}" if not has_response else f"new lines: {new_lines[:3]}")
        # Check it's not an error
        check("E8  real message — no 'ollama error' in output",
              "[ollama error]" not in final,
              final[-300:] if "[ollama error]" in final else "")

    # Wait for model to finish generating before file-tool tests
    # (E8 may still be running; file tool tests need the prompt ready)
    prompt_ready = wait_for_prompt()
    check("E8  model finished — prompt reappeared", prompt_ready,
          "model still generating after 90 s — /quit may be unreliable")

    # ── F1/F2/F3: file tool functional tests (tmux-driven) ───────────────
    # Clean up leftover test file from any prior run
    if Path(_TEST_FILE).exists():
        Path(_TEST_FILE).unlink()

    if not ollama_ok:
        skip("F1  write_file  — create /tmp test file",  "Ollama not reachable")
        skip("F2  edit_file   — update /tmp test file",  "Ollama not reachable")
        skip("F3  delete_file — remove /tmp test file",  "Ollama not reachable")
    else:
        # ── F1: write_file ────────────────────────────────────────────────
        send(f'use write_file to create {_TEST_FILE} with content: hello thmes')
        wait_for_prompt_with_approval()
        f1_created = Path(_TEST_FILE).exists()
        f1_content = (Path(_TEST_FILE).read_text(encoding="utf-8").strip()
                      if f1_created else "")
        check("F1  write_file  — file created on disk",
              f1_created, f"not found: {_TEST_FILE}" if not f1_created else "")
        check("F1  write_file  — content matches",
              "hello thmes" in f1_content,
              f"content: {f1_content!r}" if f1_created else "file missing")

        # ── F2: edit_file ─────────────────────────────────────────────────
        if f1_created:
            send(f'use edit_file to replace "hello thmes" with "hello world" in {_TEST_FILE}')
            wait_for_prompt_with_approval()
            f2_content = (Path(_TEST_FILE).read_text(encoding="utf-8").strip()
                          if Path(_TEST_FILE).exists() else "")
            check("F2  edit_file   — content updated on disk",
                  "hello world" in f2_content,
                  f"content: {f2_content!r}")
        else:
            skip("F2  edit_file   — update /tmp test file", "F1 did not create file")

        # ── F3: delete_file ───────────────────────────────────────────────
        if Path(_TEST_FILE).exists():
            send(f'use delete_file to remove {_TEST_FILE}')
            wait_for_prompt_with_approval()
            check("F3  delete_file — file removed from disk",
                  not Path(_TEST_FILE).exists(),
                  f"file still exists: {_TEST_FILE}")
        else:
            skip("F3  delete_file — remove /tmp test file", "no test file to delete")

        # Cleanup — remove test file if any tool failed silently
        if Path(_TEST_FILE).exists():
            Path(_TEST_FILE).unlink()

    # Wait for the last F-series model turn to fully finish before /quit
    wait_for_prompt()

    # Dismiss any lingering "new session?" prompt before /quit
    # Use scrollback=0 — only check current viewport, not history
    if "session ใหม่ไหม?" in capture(scrollback=0):
        send("n", enter=True)
        time.sleep(0.5)

    # ── E9: /quit ────────────────────────────────────────────────────────
    # Pipe pane output to a temp file BEFORE sending /quit so we catch
    # "bye" even if the process exits before the next capture() call.
    bye_log = "/tmp/gemma_e2e_quit.log"
    _tmux("pipe-pane", "-t", SESSION, "-o", f"cat >> {bye_log}")
    if Path(bye_log).exists():
        Path(bye_log).unlink()

    send("/quit")
    time.sleep(1.0)     # give the app time to print "bye" and exit

    # Stop piping; read the log
    _tmux("pipe-pane", "-t", SESSION)   # stop pipe
    logged = Path(bye_log).read_text(errors="replace") if Path(bye_log).exists() else ""
    scrollback_now = capture()
    bye_seen = "bye" in logged or "bye" in scrollback_now

    # Process exit: session gone OR shell prompt visible
    sessions_out = subprocess.run(["tmux", "list-sessions"],
                                  capture_output=True, text=True).stdout
    session_gone = SESSION not in sessions_out
    time.sleep(0.5)
    final_pane = capture(scrollback=0)
    last_lines = final_pane.splitlines()[-8:]
    shell_visible = any(
        line.rstrip().endswith(("% ", "$ ", "% ", "%", "$"))
        or line.strip() in ("%", "$", "~ %", "~ $")
        for line in last_lines
    )

    check("E9  /quit — 'bye' printed",
          bye_seen,
          f"logged={logged[-200:]!r}  scrollback={scrollback_now[-100:]!r}"
          if not bye_seen else "")
    check("E9  /quit — process exited (shell prompt or session gone)",
          shell_visible or session_gone,
          f"last lines: {last_lines}")

finally:
    kill_session()   # no-op if already gone

# ── Summary ───────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
total   = len(results)
passed  = sum(1 for _, ok, _ in results if ok)
skipped = sum(1 for _, _, d in results if d.startswith("SKIP:"))
failed  = total - passed
print(f"Total: {total}  PASS: {passed}  SKIP: {skipped}  FAIL: {failed}")
if failed:
    print("\nFailed:")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL  {name}")
            if detail:
                print(f"        {detail[:300]}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
