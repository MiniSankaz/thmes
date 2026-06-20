"""thmes_notify — Desktop notifications (macOS via osascript).

Optional features:
  • notify_done(elapsed_s) — only fire if elapsed > threshold (long tasks)
  • notify_error(title, body) — always fire on error
  • notify_orchestration_done(run_id, status, steps)
"""
from __future__ import annotations
import os
import shutil
import subprocess


# Settings (overridable per call)
DEFAULT_THRESHOLD_S = 30.0   # only notify if task took > this
DEFAULT_SOUND = "Glass"      # macOS sound name; set to "" to silence


_HAS_OSASCRIPT = shutil.which("osascript") is not None


def _safe(text: str, max_len: int = 200) -> str:
    return text.replace('"', '\\"').replace("\n", " ")[:max_len]


def send(title: str, body: str, sound: str | None = None, subtitle: str = "") -> bool:
    """Send a macOS desktop notification. Returns True if dispatched."""
    if not _HAS_OSASCRIPT: return False
    parts = [f'display notification "{_safe(body)}" with title "{_safe(title)}"']
    if subtitle:
        parts.append(f'subtitle "{_safe(subtitle, 80)}"')
    if sound is None: sound = DEFAULT_SOUND
    if sound:
        parts.append(f'sound name "{_safe(sound, 40)}"')
    script = " ".join(parts)
    try:
        subprocess.run(["osascript", "-e", script], check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=5)
        return True
    except Exception:
        return False


def notify_done(action: str, elapsed_s: float, summary: str = "",
                 threshold: float = DEFAULT_THRESHOLD_S) -> bool:
    """Notify if action took longer than threshold (don't spam for quick ops)."""
    if elapsed_s < threshold: return False
    body = f"{summary[:100]} ({elapsed_s:.0f}s)" if summary else f"took {elapsed_s:.0f}s"
    return send(f"✓ {action}", body, subtitle="thmes-pro")


def notify_error(title: str, body: str) -> bool:
    """Always-on notify for errors."""
    return send(f"✗ {title}", body, sound="Basso", subtitle="thmes-pro")


def notify_goal_done(goal_id: str, goal_text: str, status: str, run_id: str = "") -> bool:
    icon = "✓" if status == "completed" else "✗"
    body = f"{goal_text[:80]}"
    if run_id: body += f" (run {run_id[:8]})"
    sound = "Glass" if status == "completed" else "Basso"
    return send(f"{icon} goal {goal_id[:8]}", body,
                sound=sound, subtitle=f"status={status}")


def notify_orchestration_done(run_id: str, status: str,
                                completed: int, total: int) -> bool:
    icon = "✓" if status == "completed" else "✗"
    body = f"{completed}/{total} steps"
    sound = "Glass" if status == "completed" else "Basso"
    return send(f"{icon} orchestration {run_id[:8]}",
                body, sound=sound, subtitle=f"status={status}")
