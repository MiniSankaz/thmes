```
████████╗██╗  ██╗███╗   ███╗███████╗███████╗
╚══██╔══╝██║  ██║████╗ ████║██╔════╝██╔════╝
   ██║   ███████║██╔████╔██║█████╗  ███████╗
   ██║   ██╔══██║██║╚██╔╝██║██╔══╝  ╚════██║
   ██║   ██║  ██║██║ ╚═╝ ██║███████╗███████║
   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝
```

<div align="center">

### Thai Hermes Agentic Shell

An agentic terminal for local **MLX / Ollama** models<br>
🛡️ privacy relay&nbsp; · &nbsp;🤖 agentic tools&nbsp; · &nbsp;🔧 self-heal&nbsp; · &nbsp;🌐 browser terminal

![ci](https://github.com/MiniSankaz/thmes/actions/workflows/ci.yml/badge.svg)
![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-444?style=flat-square)
![python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![models](https://img.shields.io/badge/models-MLX%20%7C%20Ollama-FF6F00?style=flat-square)
![privacy](https://img.shields.io/badge/privacy-relay%20(no%20data%20leaves)-2ea44f?style=flat-square)
![license](https://img.shields.io/badge/license-MIT%20%2B%20Commons%20Clause-blue?style=flat-square)

**[🇹🇭 ไทย](#ภาษาไทย)&nbsp; · &nbsp;[🇬🇧 English](#english)**

</div>

> ⚠️ **Preview release** — ใช้งานได้แต่ API/CLI อาจเปลี่ยนโดยไม่แจ้งล่วงหน้า feedback ยินดีรับที่ [Issues](https://github.com/MiniSankaz/thmes/issues)

---

## ภาษาไทย

Agentic terminal UI สำหรับ **MLX / Ollama** model บน local: built-in tools, smart router เลือก context เอง, persistent session บน SQLite, MCP integration, multi-tier semantic memory, multi-source research, **privacy relay** และ **web terminal**

### ✨ Highlights

- รองรับทั้ง **MLX** model (local) และ **Ollama** (local + cloud ที่ `ollama signin` แล้ว เช่น `gpt-oss:120b-cloud`)
- **Privacy relay** — ใช้ cloud model ตัวแรง reason/act กับ data ของคุณ โดย**ค่าจริงไม่ออกนอกเครื่อง**
- **Agentic tools + self-heal** — cloud สั่ง tool call, local execute จริง, แล้ว loop verify → triage error → re-ask cloud เพื่อ fix เอง
- **Web terminal** — เปิด full CLI ใน browser (PTY + WebSocket + xterm.js) ทุกอย่าง run บน local

### 📂 Project Structure

```
thmes/
├── bin/                      # Executables
│   ├── thmes                 # Main UI (Rich + prompt_toolkit)
│   ├── thmes-pro             # Multi-pane UI (Textual, experimental)
│   ├── thmes-daemon          # Background goal worker
│   ├── thmes-web             # Web terminal launcher → web/server.py
│   ├── gemma                 # One-shot CLI / --server (OpenAI-compatible :8081)
│   ├── mlx-serve-{gemma,qwen,qwen3}   # MLX HTTP server
│   └── hermes-use            # Point Hermes ไปที่ local model
├── lib/                      # Python modules
│   ├── thmes_mask.py         # ★ Privacy relay masking engine
│   ├── thmes_mcp.py          # MCP client
│   ├── thmes_memory.py       # Multi-tier memory + embeddings
│   ├── thmes_orchestrator.py # Multi-step orchestrator (L2)
│   ├── thmes_goals.py        # Autonomous goal queue (L3)
│   └── thmes_registry.py     # Hot-swap model registry
├── web/                      # ★ Web terminal (server.py + index.html)
├── agents/                   # 12 agent personas (5 files each: JSON/txt)
├── tests/                    # Regression tests (test_r_*.py — run real code)
├── docs/                     # CODEMAP.md (source index) · ROADMAP.md
├── install.sh / install.ps1  # Installers (Unix / Windows)
└── README.md
```

### 🚀 Quick Start

**macOS / Linux** — install symlink เข้า `~/.local/bin` (อยู่ใน `PATH`):
```bash
./install.sh                 # symlink/wrapper สำหรับ bin/* (idempotent — run ซ้ำได้)
```

**Windows** (PowerShell) — สร้าง `.cmd` shim บน user `PATH`:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
> Windows support แบบ **best-effort**: TUI run ผ่าน **Ollama** ได้ (ไม่มี MLX) แต่ `bash` tool, `gemma`, `mlx-serve-*` และ **web terminal** เป็น Unix-only — ถ้าต้องการ full feature ให้ run ผ่าน **WSL**

จากนั้น (เปิด terminal ใหม่ก่อน):
```bash
thmes                        # main UI
thmes-pro                    # multi-pane UI (experimental)
```

Runtime data ถูกสร้าง auto ใน `~/.thmes/` (override location ด้วย `THMES_HOME=/path`):

| Path | Purpose |
|---|---|
| `~/.thmes/data/sessions.db` | Persistent chat sessions |
| `~/.thmes/data/memory.db` | Memory + embeddings |
| `~/.thmes/mcp.json` | MCP config (optional) |
| `~/.thmes-history` | Input history |

### 🎛 Key Features

| Feature | Usage |
|---|---|
| Smart router — model เลือก tools/agent/skills เอง | Auto on startup |
| 12 agent personas | `/agent NAME` |
| 13 skill workflows | `/skill NAME` |
| 17 built-in tools (read/write/edit/bash/python/grep/web/make_report/…) | `/tool list` |
| Persistent SQLite sessions | `/session list\|load\|new` |
| Auto-compact context ที่ 60% | `/compact threshold N` |
| Circuit breaker (fail 3 ครั้ง → cooldown 15s) | `/breakers` |
| Deterministic multi-source research | `/research Q` |
| **Privacy relay** (mask → cloud → unmask) | `/relay …` (ดูด้านล่าง) |
| **Web terminal** ใน browser | `thmes-web` |
| Semantic memory | `/memory recall Q` |
| Image + audio | `/image PATH` · `/audio PATH` |
| กด ESC cancel generation/tool | `ESC` |

### 🛡️ Privacy Relay

ใช้ **cloud** model ตัวแรงโดยที่ sensitive data ไม่ออกนอกเครื่องเลย — local model เป็น trusted middle layer:

```
real text ─MASK (local)─▶ cloud เห็นแค่ __PII_*__ ─REASON─▶ ─UNMASK (local)─▶ user
                          ▲ leak-scan abort ทันทีถ้า real value/secret จะหลุดออก
```

Hybrid masking: regex (email/phone/Thai-ID/credit-card/API-key/.env/IP/path) + local-model NER (person/org/project) + deny-list — vault อยู่ใน RAM per-session **ไม่ write disk ไม่ send cloud**

3 modes:

| Mode | Description |
|---|---|
| **One-shot** `/relay on` | Cloud reason บน masked text, ไม่มี tools |
| **Agentic** `/relay tools on` | Cloud สั่ง tool call → **local execute จริง** (unmask args just-in-time, re-mask results) |
| **Self-heal** `/relay verify <cmd>` | Run verify → fail → local model triage error → cloud fix, loop |

```bash
/relay on                    # Enter relay mode (smoke-test cloud ก่อน)
/relay model gpt-oss:120b-cloud   # Pick cloud "brain" (ต้อง ollama signin)
/relay tools on              # Cloud drive tools, local execute
/relay verify "python -m pytest"  # Self-heal: verify → triage → re-ask cloud
/relay status                # View status · /relay deny add "Project X"
```

> Over-masking preferred — tool args จะ unmask ที่ local ก่อน execute (approval prompt แสดง **real** action)

### 🌐 Web Terminal

Run full `thmes` CLI ใน browser — `thmes-web` spawn REPL ใน pseudo-terminal แล้ว bridge เข้า [xterm.js](https://xtermjs.org/) ผ่าน WebSocket ได้ full CLI (routing/tools/sessions/relay) ใน browser, ทุกอย่าง run local

```bash
pip install websockets       # Install ครั้งเดียว
thmes-web                    # → open http://localhost:8765
```

> ถ้า `thmes` shebang python ไม่มีบนเครื่องนี้ set `THMES_CMD="/path/to/python /path/to/bin/thmes"` — ดู `web/README.md`

### 🧠 Models

| Alias | Repo / Tag |
|---|---|
| `gemma` | `mlx-community/gemma-4-e4b-it-4bit` |
| `qwen-vl` *(default)* | `mlx-community/Qwen3-VL-8B-Instruct-4bit` |
| `qwen3` | `mlx-community/Qwen3-8B-4bit` |
| `ol:<tag>` | Ollama model ใดก็ได้ เช่น `ol:gemma4:e4b`, `ol:qwen2.5-coder:7b` |
| `<tag>:cloud` | Ollama **cloud** model (ต้อง `ollama signin`) เช่น `gpt-oss:120b-cloud` |

```bash
THMES_MODEL=gemma thmes      # or  THMES_MODEL=ol:gemma4:e4b
```

### 🔧 Dependencies

Python 3.11+ ใน virtualenv (เช่น `~/.mlx-env/` หรือ `~/.thmes-env/`):
```bash
mlx, mlx-vlm, mlx-lm, mlx-embeddings, mlx-audio   # MLX models
rich, prompt_toolkit, textual                     # UI
ddgs, trafilatura, beautifulsoup4, lxml           # Web tools
mcp, huggingface_hub, transformers, safetensors
websockets                                        # Web terminal only
```

### 🛠 Development / Uninstall

Edit files ได้เลย — มีผลทันทีเพราะ symlink (no build step); อ่าน `docs/CODEMAP.md` ก่อน scan code; run tests: `python -m pytest tests/`

```bash
./uninstall.sh                                # macOS/Linux
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1   # Windows
rm -rf ~/.thmes                  # Remove runtime data (optional)
```

---

## English

An agentic terminal UI for local **MLX / Ollama** models: built-in tools, a smart context router, persistent SQLite sessions, MCP integration, multi-tier semantic memory, deterministic multi-source research, a **privacy relay**, and a **browser terminal**.

### ✨ Highlights

- Works with **local MLX** models *and* **Ollama** (local + signed-in cloud tags like `gpt-oss:120b-cloud`).
- **Privacy relay** — let a strong cloud model reason/act on your data while **no real value ever leaves the machine**.
- **Agentic tools + self-heal** — the cloud decides tool calls, this machine executes them, and a verify → triage → re-ask loop fixes failures automatically.
- **Web terminal** — the full CLI in a browser tab (PTY + WebSocket + xterm.js), all local.

### 📂 Project structure

```
thmes/
├── bin/                      # Executables
│   ├── thmes                 # Classic Rich + prompt_toolkit UI (main entry)
│   ├── thmes-pro             # Textual multi-pane UI (experimental)
│   ├── thmes-daemon          # Background goal worker
│   ├── thmes-web             # Browser terminal launcher → web/server.py
│   ├── gemma                 # One-shot CLI / --server (OpenAI-compatible :8081)
│   ├── mlx-serve-{gemma,qwen,qwen3}   # MLX HTTP servers
│   └── hermes-use            # Point Hermes at a local model
├── lib/                      # Python modules
│   ├── thmes_mask.py         # ★ Privacy-relay masking engine (MaskVault)
│   ├── thmes_mcp.py          # MCP client
│   ├── thmes_memory.py       # Multi-tier memory + embeddings
│   ├── thmes_orchestrator.py # L2 multi-step orchestrator
│   ├── thmes_goals.py        # L3 autonomous goal queue
│   └── thmes_registry.py     # Hot-swap model registry
├── web/                      # ★ Browser terminal (server.py + index.html)
├── agents/                   # 12 agent identity bundles (5 files each)
├── tests/                    # Regression tests (test_r_*.py — EXECUTE real code)
├── docs/                     # CODEMAP.md (source index) · ROADMAP.md
├── install.sh / install.ps1  # Installers (Unix / Windows)
└── README.md
```

### 🚀 Quick start

**macOS / Linux** — symlink the binaries into `~/.local/bin` (on `PATH`):
```bash
./install.sh                 # symlinks/wrappers for bin/* (idempotent — safe to re-run)
```

**Windows** (PowerShell) — create `.cmd` shims on your user `PATH`:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
> Windows is **best-effort**: the TUI runs against **Ollama** (no MLX), but the `bash` tool, `gemma`, `mlx-serve-*` and the **web terminal** are Unix-only — run thmes under **WSL** for those.

Then run (open a new terminal first):
```bash
thmes                        # main UI
thmes-pro                    # Textual multi-pane UI (experimental)
```

Runtime data is auto-created under `~/.thmes/` (override the location with `THMES_HOME=/path`):

| Path | Purpose |
|---|---|
| `~/.thmes/data/sessions.db` | persistent chat sessions |
| `~/.thmes/data/memory.db` | L2–L4 memory + embeddings |
| `~/.thmes/mcp.json` | MCP server config (optional) |
| `~/.thmes-history` | input history |

### 🎛 Key features

| Feature | How |
|---|---|
| Smart router — model picks its own tools/agent/skills | auto on startup |
| 12 agent personas | `/agent NAME` |
| 13 skill workflows | `/skill NAME` |
| 17 built-in tools (read/write/edit/bash/python/grep/web/make_report/…) | `/tool list` |
| Persistent SQLite sessions | `/session list\|load\|new` |
| Auto-compact at 60% context | `/compact threshold N` |
| Circuit breaker (3 fails → 15s) | `/breakers` |
| Deterministic multi-source research | `/research Q` |
| **Privacy relay** (mask → cloud → unmask) | `/relay …` (see below) |
| **Web terminal** in the browser | `thmes-web` |
| Semantic memory (embeddings) | `/memory recall Q` |
| Multimodal (image + audio) | `/image PATH` · `/audio PATH` |
| ESC to interrupt generation/tools | `ESC` |

### 🛡️ Privacy relay

Use a strong **cloud** model without sensitive data ever leaving your machine — the local model is the trusted middle layer:

```
real text ─MASK (local)─▶ cloud sees only __PII_*__ ─REASON─▶ ─UNMASK (local)─▶ you
                          ▲ leak-scan aborts if any real value/secret would go out
```

Hybrid masking: regex (email/phone/Thai-ID/card/API-key/.env-secret/IP/path) + local-model NER (person/org/project) + a user deny-list. The real↔token vault is **in-RAM, per-session, never written to disk or sent to the cloud**.

Three modes:

| Mode | What it does |
|---|---|
| **One-shot** `/relay on` | cloud reasons over masked text, no tools |
| **Agentic** `/relay tools on` | cloud decides tool calls → **this machine executes** (args unmasked just-in-time, results re-masked) |
| **Self-heal** `/relay verify <cmd>` | run a verify cmd → on failure the local model triages the error → cloud fixes, looping |

```bash
/relay on                    # enter relay (smoke-tests the cloud model first)
/relay model gpt-oss:120b-cloud   # pick the cloud "brain" (needs `ollama signin`)
/relay tools on              # let the cloud drive tools, executed locally
/relay verify "python -m pytest"  # self-heal: verify → triage → re-ask the cloud
/relay status                # see everything · /relay deny add "Project X"
```

> Over-masking is preferred to under-masking; tool **arguments** are unmasked locally before execution (the approval prompt shows the **real** action).

### 🌐 Web terminal

Run the real `thmes` CLI in a browser tab. `thmes-web` spawns the REPL in a pseudo-terminal and bridges it to [xterm.js](https://xtermjs.org/) over a WebSocket — the full CLI (routing, tools, sessions, relay) in the browser, all local.

```bash
pip install websockets       # one-time dependency
thmes-web                    # → open http://localhost:8765
```

> If the `thmes` shebang Python isn't on this host, set `THMES_CMD="/path/to/python /path/to/bin/thmes"`. See `web/README.md`.

### 🧠 Models

| Alias | Repo / Tag |
|---|---|
| `gemma` | `mlx-community/gemma-4-e4b-it-4bit` |
| `qwen-vl` *(default)* | `mlx-community/Qwen3-VL-8B-Instruct-4bit` |
| `qwen3` | `mlx-community/Qwen3-8B-4bit` |
| `ol:<tag>` | any Ollama model, e.g. `ol:gemma4:e4b`, `ol:qwen2.5-coder:7b` |
| `<tag>:cloud` | Ollama **cloud** models (need `ollama signin`), e.g. `gpt-oss:120b-cloud` |

```bash
THMES_MODEL=gemma thmes      # or  THMES_MODEL=ol:gemma4:e4b
```

### 🔧 Dependencies

Python 3.11+ in a virtualenv (e.g. `~/.mlx-env/` or `~/.thmes-env/`):
```bash
mlx, mlx-vlm, mlx-lm, mlx-embeddings, mlx-audio   # local MLX models
rich, prompt_toolkit, textual                     # UI
ddgs, trafilatura, beautifulsoup4, lxml           # web tools
mcp, huggingface_hub, transformers, safetensors
websockets                                        # web terminal only
```

### 🛠 Development / Uninstall

Edit files here directly — changes take effect immediately (symlink, no build). See `docs/CODEMAP.md` before scanning code; run tests with `~/.mlx-env/bin/python -m pytest tests/`.

```bash
./uninstall.sh                                # macOS/Linux
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1   # Windows
rm -rf ~/.thmes                  # runtime data (optional)
```

---

*v0.1.0-preview.1 — agentic relay · self-heal · web terminal · cross-platform installers*
