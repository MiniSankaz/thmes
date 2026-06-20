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

> ⚠️ **Synced repo** · this project is synced across machines (different usernames, paths, models) — don't commit machine-specific paths/shebangs/model names; override at the call site (env var).
> **รีโปนี้ sync หลายเครื่อง** — อย่า commit ค่าเฉพาะเครื่อง ให้ override ที่ call site (env var)

---

## ภาษาไทย

เทอร์มินัล UI แบบ agentic สำหรับโมเดล **MLX / Ollama** ในเครื่อง: มีเครื่องมือในตัว, smart router เลือก context เอง, session ถาวรบน SQLite, รองรับ MCP, memory เชิงความหมายหลายชั้น, research หลายแหล่ง, **privacy relay** และ **เทอร์มินัลบนเบราว์เซอร์**

### ✨ ไฮไลต์

- ใช้ได้ทั้งโมเดล **MLX** ในเครื่อง และ **Ollama** (ทั้ง local และ cloud ที่ `ollama signin` แล้ว เช่น `gpt-oss:120b-cloud`)
- **Privacy relay** — ใช้โมเดล cloud ตัวแรงคิด/ทำงานกับข้อมูลของคุณ โดย**ค่าจริงไม่ออกนอกเครื่อง**
- **Agentic tools + self-heal** — cloud สั่งใช้ tool, เครื่องนี้รันจริง, แล้ววน verify → วิเคราะห์ error → ถาม cloud ใหม่เพื่อแก้เอง
- **Web terminal** — เปิด CLI เต็มในเบราว์เซอร์ (PTY + WebSocket + xterm.js) ทุกอย่างรันในเครื่อง

### 📂 โครงสร้างโปรเจกต์

```
thmes/
├── bin/                      # ไฟล์รัน
│   ├── thmes                 # UI หลัก (Rich + prompt_toolkit)
│   ├── thmes-pro             # UI หลายแพเนล (Textual, ทดลอง)
│   ├── thmes-daemon          # ตัวรัน goal เบื้องหลัง
│   ├── thmes-web             # ตัวเปิด web terminal → web/server.py
│   ├── gemma                 # CLI ครั้งเดียว / --server (OpenAI-compatible :8081)
│   ├── mlx-serve-{gemma,qwen,qwen3}   # MLX HTTP server
│   └── hermes-use            # ชี้ Hermes ไปโมเดล local
├── lib/                      # โมดูล Python
│   ├── thmes_mask.py         # ★ เอนจิน masking ของ privacy relay
│   ├── thmes_mcp.py          # MCP client
│   ├── thmes_memory.py       # memory หลายชั้น + embeddings
│   ├── thmes_orchestrator.py # orchestrator หลายสเต็ป (L2)
│   ├── thmes_goals.py        # คิว goal อัตโนมัติ (L3)
│   └── thmes_registry.py     # registry สลับโมเดลแบบ hot-swap
├── web/                      # ★ เทอร์มินัลบนเว็บ (server.py + index.html)
├── agents/                   # 12 เพอร์โซนา (ชุดละ 5 ไฟล์ JSON/txt)
├── tests/                    # เทสต์ regression (test_r_*.py — รันโค้ดจริง)
├── docs/                     # CODEMAP.md (ดัชนีโค้ด) · ROADMAP.md
├── install.sh / install.ps1  # ตัวติดตั้ง (Unix / Windows)
└── README.md
```

### 🚀 เริ่มใช้งาน

**macOS / Linux** — ติดตั้ง symlink เข้า `~/.local/bin` (อยู่ใน `PATH`):
```bash
./install.sh                 # symlink/wrapper ของ bin/* (idempotent รันซ้ำได้)
```

**Windows** (PowerShell) — สร้าง `.cmd` shim บน user `PATH`:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```
> Windows รองรับแบบ **best-effort**: TUI รันผ่าน **Ollama** ได้ (ไม่มี MLX) แต่ `bash` tool, `gemma`, `mlx-serve-*` และ **web terminal** เป็น Unix-only — ถ้าต้องการครบให้รันผ่าน **WSL**

จากนั้น (เปิดเทอร์มินัลใหม่ก่อน):
```bash
thmes                        # UI หลัก
thmes-pro                    # UI หลายแพเนล (ทดลอง)
```

ข้อมูลตอนรันถูกสร้างอัตโนมัติใน `~/.thmes/` (เปลี่ยนที่เก็บด้วย `THMES_HOME=/path`):

| Path | ใช้ทำอะไร |
|---|---|
| `~/.thmes/data/sessions.db` | session แชตถาวร |
| `~/.thmes/data/memory.db` | memory + embeddings |
| `~/.thmes/mcp.json` | คอนฟิก MCP (ไม่บังคับ) |
| `~/.thmes-history` | ประวัติ input |

### 🎛 คุณสมบัติเด่น

| คุณสมบัติ | วิธีใช้ |
|---|---|
| Smart router — โมเดลเลือก tools/agent/skills เอง | อัตโนมัติตอนเริ่ม |
| 12 เพอร์โซนา | `/agent NAME` |
| 13 สกิล | `/skill NAME` |
| 17 เครื่องมือในตัว (read/write/edit/bash/python/grep/web/make_report/…) | `/tool list` |
| session ถาวรบน SQLite | `/session list\|load\|new` |
| ย่อ context อัตโนมัติที่ 60% | `/compact threshold N` |
| Circuit breaker (พัง 3 ครั้ง → พัก 15 วิ) | `/breakers` |
| research หลายแหล่งแบบ deterministic | `/research Q` |
| **Privacy relay** (ปิดบัง → cloud → ถอดคืน) | `/relay …` (ดูด้านล่าง) |
| **Web terminal** ในเบราว์เซอร์ | `thmes-web` |
| memory เชิงความหมาย | `/memory recall Q` |
| รูป + เสียง | `/image PATH` · `/audio PATH` |
| กด ESC ยกเลิกการ gen/tool | `ESC` |

### 🛡️ Privacy relay

ใช้โมเดล **cloud** ตัวแรงโดยที่ข้อมูลอ่อนไหวไม่ออกนอกเครื่องเลย — โมเดล local เป็นชั้นกลางที่เชื่อถือได้:

```
ข้อความจริง ─MASK (local)─▶ cloud เห็นแต่ __PII_*__ ─REASON─▶ ─UNMASK (local)─▶ ผู้ใช้
                           ▲ leak-scan ยกเลิกทันทีถ้าค่าจริง/secret จะหลุดออก
```

ปิดบังแบบไฮบริด: regex (อีเมล/เบอร์/เลขบัตร ปชช./บัตรเครดิต/API-key/.env/IP/path) + NER จากโมเดล local (ชื่อคน/องค์กร/โปรเจกต์) + deny-list — vault อยู่ใน RAM ต่อ session **ไม่เขียนดิสก์ ไม่ส่ง cloud**

มี 3 โหมด:

| โหมด | ทำอะไร |
|---|---|
| **One-shot** `/relay on` | cloud คิดบนข้อความที่ปิดบัง ไม่มี tool |
| **Agentic** `/relay tools on` | cloud สั่งใช้ tool → **เครื่องนี้รันจริง** (ถอด args ตอนรัน, ปิดบังผลลัพธ์ก่อนส่งกลับ) |
| **Self-heal** `/relay verify <cmd>` | รัน verify → ถ้า fail โมเดล local วิเคราะห์ error → cloud แก้ วนเอง |

```bash
/relay on                    # เข้าโหมด relay (smoke-test cloud ก่อน)
/relay model gpt-oss:120b-cloud   # เลือก cloud "สมอง" (ต้อง ollama signin)
/relay tools on              # ให้ cloud สั่ง tool, รันในเครื่อง
/relay verify "python -m pytest"  # self-heal: verify → วิเคราะห์ → ถาม cloud ใหม่
/relay status                # ดูสถานะทั้งหมด · /relay deny add "Project X"
```

> ระบบเลือกปิดบังเกินไว้ก่อนเพื่อความปลอดภัย; args ของ tool ถูกถอดคืนในเครื่องก่อนรัน (หน้าจอ approval โชว์ action **จริง**)

### 🌐 Web terminal

เปิด `thmes` CLI ตัวจริงในเบราว์เซอร์ — `thmes-web` รัน REPL ใน pseudo-terminal แล้วต่อเข้า [xterm.js](https://xtermjs.org/) ผ่าน WebSocket ได้ CLI เต็ม (routing/tools/sessions/relay) ในเบราว์เซอร์ ทุกอย่างรันในเครื่อง

```bash
pip install websockets       # ติดตั้งครั้งเดียว
thmes-web                    # → เปิด http://localhost:8765
```

> ถ้า shebang python ของ `thmes` ไม่มีในเครื่องนี้ ตั้ง `THMES_CMD="/path/to/python /path/to/bin/thmes"` — ดู `web/README.md`

### 🧠 โมเดล

| Alias | Repo / Tag |
|---|---|
| `gemma` | `mlx-community/gemma-4-e4b-it-4bit` |
| `qwen-vl` *(default)* | `mlx-community/Qwen3-VL-8B-Instruct-4bit` |
| `qwen3` | `mlx-community/Qwen3-8B-4bit` |
| `ol:<tag>` | โมเดล Ollama ใด ๆ เช่น `ol:gemma4:e4b`, `ol:qwen2.5-coder:7b` |
| `<tag>:cloud` | โมเดล Ollama **cloud** (ต้อง `ollama signin`) เช่น `gpt-oss:120b-cloud` |

```bash
THMES_MODEL=gemma thmes      # หรือ THMES_MODEL=ol:gemma4:e4b
```

### 🔧 ไลบรารีที่ต้องใช้

Python 3.11+ ใน virtualenv (เช่น `~/.mlx-env/` หรือ `~/.thmes-env/`):
```bash
mlx, mlx-vlm, mlx-lm, mlx-embeddings, mlx-audio   # โมเดล MLX
rich, prompt_toolkit, textual                     # UI
ddgs, trafilatura, beautifulsoup4, lxml           # web tools
mcp, huggingface_hub, transformers, safetensors
websockets                                        # เฉพาะ web terminal
```

### 🛠 การพัฒนา / ถอนการติดตั้ง

แก้ไฟล์ได้เลย — มีผลทันทีเพราะ symlink (ไม่มี build); อ่าน `docs/CODEMAP.md` ก่อนไล่โค้ด; รันเทสต์: `~/.mlx-env/bin/python -m pytest tests/`

```bash
./uninstall.sh                                # macOS/Linux
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1   # Windows
rm -rf ~/.thmes                  # ลบข้อมูลตอนรัน (ไม่บังคับ)
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

*v0.5 — agentic relay · self-heal · web terminal · cross-platform installers*
