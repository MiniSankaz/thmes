# Changelog

All notable changes to **thmes** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versions track the
`VERSION` constant in `bin/thmes`.

## [0.4.1] — 2026-06-23

Theme: smarter, **model-aware tool routing**.

### Added
- **Adaptive per-model tool-calling mode** — thmes calibrates each model once (a small
  labelled probe) to pick native function-calling vs the inline-text protocol, caches the
  verdict to `~/.thmes/data/tool_mode.json`, and exposes `THMES_TOOL_MODE` (auto|native|text)
  plus a `/toolmode` command (view / force / recalibrate / clear). Default stays native.
- **"When NOT to call a tool" guidance** in the tool system prompt — greetings,
  acknowledgements, approvals, and coordination get a plain-text reply instead of a spurious
  tool call.

### Changed
- **Expanded keyword router net** — added current-directory detection (was missing entirely),
  broadened date/time, and taught read/list/grep/delete/edit to recognise a real
  filename / extension / path instead of only the literal word "file". On a clean local-model
  benchmark this lifted small-model tool selection ~64% → ~88%, with no regression on larger
  models.

## [0.4.0] — 2026-06-22

Theme: let the **local** model do real file work without data leaving the machine, let the
**LLM** decide routing (not keyword regex), and make the **web UI** work out of the box.

### Added
- **Local-only relay** (`/relay local on`, flag `relay_local`) — the cloud is a *director*
  that emits one step at a time and only ever sees short, content-free status reports; the
  local model does every read/edit/run on real data. File content never leaves the machine,
  not even masked.
- **Working directory** — a project root (defaults to the launch dir) that all relative file
  paths, grep, and shell/python resolve against. Change it via `/cd`, `/pwd`, or the new
  `set_workdir` tool.
- **Office-document reading** — `read_file` auto-extracts `.xlsx/.xlsm`, `.pptx`, `.docx` to
  text (optional `openpyxl`/`python-pptx`/`python-docx`, else a stdlib `zipfile`+`xml`
  fallback). CSV/code/text read verbatim; unknown binaries return an honest note.
- **Version surfacing** — `VERSION` constant shown in the startup banner, the live header
  strip, and `thmes --version`.
- **Self-bootstrapping web UI** — `thmes-web` auto-picks a Python with `websockets`
  (installing it on demand) and serves *this* checkout's CLI; `install.sh` pre-installs the
  web dep so `dev-thmes-web` works on first run.

### Changed
- **Ollama-first default** — when `THMES_MODEL` isn't pinned, startup prefers an available
  Ollama model over the MLX default (the `DEFAULT_MODEL` constant is unchanged — sync-safe).
  MLX-only machines keep MLX; an explicit pin always wins.
- **Router decides web-vs-local (no keyword regex)** — the LLM router now drives the
  auto-research decision: it fires only when the router picked a web tool **and** no
  local/file tool. `ROUTER_PROMPT` emits a `web` hint, the keyword fast-path defers
  ambiguous "ล่าสุด/latest" to the LLM, and an empty tool selection loads the full toolset
  instead of crippling the agent. `_RESEARCH_TRIGGER_RE` is now only the no-router fallback.

### Fixed
- **Relay premature termination** — in agentic relay, a cloud turn that narrated its next
  step as prose (no tool call) ended the task early. A bounded action-nudge now pushes the
  cloud to emit the call, so multi-step read→process→write tasks complete.
- **Web UI on a dev box** — `dev-thmes-web` ran with bare `python3` (no `websockets`) and
  spawned the *public* CLI from PATH; it now resolves a dep-complete Python and serves the
  dev CLI. Non-WebSocket probes to the bridge port no longer dump handshake tracebacks.

### Notes
- Verified end-to-end against Ollama (no MLX on the test host): Office-doc reading 100% on
  gemma4 e2b/e4b + typhoon2.5; a 206-case TH/EN router stress test (local categories ~100%;
  the residual misses are genuine small-model ambiguity on "X ล่าสุด").
- Tested on an Ollama-only machine per the repo's multi-machine sync rule — no
  machine-specific values were committed.

## [0.3.0]

Baseline: single-file Python TUI with smart router, opencode delegation, salvage layer,
privacy relay (one-shot + agentic), persistent SQLite sessions, MCP, multi-tier memory,
orchestrator, autonomous goal queue. See `docs/ROADMAP.md`.
