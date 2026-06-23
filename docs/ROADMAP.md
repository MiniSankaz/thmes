# thmes — Evolution Roadmap

> From terminal chat → agentic kernel
> Inspired by [agent-kernel](https://github.com/MiniSankaz/agent-kernel) by MiniSankaz

**Current**: v0.4.0 — adds privacy-relay (one-shot/agentic/local-only), working-dir, Office-doc reading, Ollama-first default (on top of v0.3: smart router, opencode delegation, salvage layer). `VERSION` constant in `bin/thmes`; shown in banner + live header; `thmes --version`.
**Target**: v1.0 — Multi-tier agentic system with persistent memory, orchestration, autonomous goals

---

## 📐 Architecture Target (v1.0)

```
┌─────────────────────────────────────────────────────────────┐
│                    Textual TUI (Phase 1.5)                  │
│  ┌─────────┬───────────────────────────┬─────────────────┐  │
│  │ Sessions│       Chat View           │  Live Monitor   │  │
│  │ Sidebar │  (streaming markdown)     │  (stats + log)  │  │
│  ├─────────┴───────────────────────────┴─────────────────┤  │
│  │                  Input + slash commands               │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │  Status bar: model · agent · ctx% · tools · RAM       │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ L3 Autonomous│  │ L2 Orchestr- │  │  L1 ReAct Loop   │
│ Goal queue   │  │ ator (plan)  │  │  (tool calls)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────────┘
       │                 │                  │
       └────────┬────────┴──────────────────┘
                ▼
       ┌────────────────────────────────────┐
       │     SkillRouter (MCP-based)         │
       │  filesystem · github · web · bash   │
       └──────────────┬─────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌──────────┐ ┌─────────────┐
│ MLX models  │ │ opencode │ │ MCP servers │
└─────────────┘ └──────────┘ └─────────────┘
                      │
                ┌─────┴─────┐
                ▼           ▼
       ┌──────────────┐ ┌──────────────┐
       │ SQLite store │ │ Embed memory │
       │ (sessions,   │ │ (mlx nomic-  │
       │  events)     │ │  embed)      │
       └──────────────┘ └──────────────┘
```

---

## 🎯 Phase 1 — Foundation (Week 1, ~6-10 hr)

### Goals
- Persistent, resumable sessions
- Resilient tool execution
- Structured agent identity

### Deliverables

| # | Task | Estimate | Files |
|---|------|----------|-------|
| 1.1 | JSON identity loader | 1h | `~/.thmes/agents/<name>/{identity,capabilities,safeguards,config}.json` |
| 1.2 | Migrate 14 Claude agents → JSON | 1h | one-time conversion script |
| 1.3 | SQLite session store | 2h | `~/.thmes/sessions.db` (Prisma-py or sqlite3) |
| 1.4 | `/session list/load/new` commands | 1h | TUI integration |
| 1.5 | Circuit breaker for tools | 1h | per-tool failure counter + 15s cooldown |
| 1.6 | `/breakers` command + status header indicator | 0.5h | TUI |
| 1.7 | Tests (unit + integration) | 2h | extend e2e_test.sh |

### Files added
```
~/.local/bin/thmes                       # main (existing, modified)
~/.thmes/
├── agents/
│   ├── analyst/
│   │   ├── identity.json
│   │   ├── capabilities.json
│   │   ├── safeguards.json
│   │   ├── config.json
│   │   └── system-prompt.txt
│   ├── architect/...
│   └── (14 agents)
├── sessions.db                           # SQLite
└── breakers.json                         # transient state
```

### Schema — sessions.db

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,                    -- uuid
  title TEXT,                             -- auto-generated from first msg
  model TEXT, agent TEXT,
  created_at TEXT, updated_at TEXT,
  message_count INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  status TEXT DEFAULT 'active'            -- active | archived | compacted
);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT REFERENCES sessions(id),
  role TEXT,                              -- user | assistant | tool | system
  content TEXT,
  tool_call TEXT,                         -- JSON if tool
  tool_result TEXT,                       -- JSON if result
  tokens INTEGER,
  is_compacted INTEGER DEFAULT 0,
  created_at TEXT
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

### KPIs
- ✅ Restart TUI → previous session resumes
- ✅ `/session list` shows last 20 sessions with title
- ✅ Failed tool 3x → circuit opens for 15s (visible in header)
- ✅ Agent JSON files load + override system prompt

---

## 🧠 Phase 2 — Intelligence (Week 2-3, ~12-18 hr)

### Goals
- Standard MCP skill protocol (compatible with Claude Code ecosystem)
- Semantic memory (model remembers things across context boundary)
- Real-time event monitoring

### Deliverables

| # | Task | Estimate | Tech |
|---|------|----------|------|
| 2.1 | MCP client integration | 4h | `mcp` Python package |
| 2.2 | Built-in MCP servers (fs, web, bash, github) | 2h | wrap existing tools as MCP |
| 2.3 | `mcp.json` config for adding external MCP servers | 1h | similar to Claude Code |
| 2.4 | Embedding model loader | 1h | `mlx-community/nomic-embed-text-v1.5-4bit` |
| 2.5 | Memory tiers schema + insert/retrieve | 3h | sqlite-vss extension OR cosine in Python |
| 2.6 | Smart memory hooks (pre-prompt retrieve relevant) | 2h | RAG pattern |
| 2.7 | Event bus + SSE-like log | 2h | in-process pub/sub |
| 2.8 | `/monitor` split-pane mode | 1h | TUI |
| 2.9 | Tests | 2h | |

### Memory Tiers

| Tier | Lifetime | Example | Retrieval |
|---|---|---|---|
| **L1: Working** | Current turn | Tool results, prompts | passed directly |
| **L2: Episodic** | Session | Conversation history | recent N + relevant K |
| **L3: Semantic** | Permanent | User preferences, learned facts | embedding cosine search |
| **L4: Reference** | Permanent | Pinned docs, files | by key |

### Memory operations

```python
mem.store(tier="L3", key="user_pref_thai", value="ผู้ใช้ชอบให้ตอบเป็นไทย", agent="default")
mem.recall(query="user preferences", tier=["L3","L4"], top_k=5)
mem.compact(session_id="abc", keep_recent=4)   # move old → L2 summary
```

### MCP Integration

```json
// ~/.thmes/mcp.json
{
  "servers": {
    "filesystem": {"command": "mcp-server-filesystem", "args": ["/home/you"]},
    "github":     {"command": "mcp-server-github",     "env": {"GITHUB_TOKEN": "..."}},
    "memory":     {"command": "python -m thmes.mcp.memory_server"},
    "ollama":     {"command": "mcp-server-ollama"}
  }
}
```

→ Gemma gets access to **all MCP tools** the Claude Code ecosystem has

### KPIs
- ✅ Connect any 3rd-party MCP server via mcp.json
- ✅ Embed 1000-message history → recall relevant 5 in <500ms
- ✅ `/monitor` shows live tool calls + token consumption + RAM
- ✅ Cross-session: "I told you my preference last week" → recalled via L3

---

## 🤖 Phase 3 — Autonomy (Week 4-5, ~15-20 hr)

### Goals
- Multi-step planning (orchestrator)
- Background goal pursuit (autonomous)
- Hot-swappable model + agent runtime

### Deliverables

| # | Task | Estimate | Notes |
|---|------|----------|-------|
| 3.1 | L2 Orchestrator: plan → execute steps | 4h | Gemma plans, Qwen/opencode executes |
| 3.2 | Step retry + review pattern | 2h | each step optionally reviewed |
| 3.3 | `/orchestrate` command | 1h | TUI |
| 3.4 | L3 Goal queue (SQLite) | 2h | priority, status, parent goal |
| 3.5 | Background worker (separate process) | 3h | poll queue, run goals |
| 3.6 | `/goal add/list/status` commands | 1h | |
| 3.7 | Gateway notify (desktop notification) | 1h | macOS osascript |
| 3.8 | Hot-swap model registry | 1h | `getCurrentModel()` per turn |
| 3.9 | Tests | 2h | |

### Orchestrator example flow

```
User: "implement user CRUD API with tests"
  ↓
Orchestrator plans (Gemma):
  step 1: agent=architect    "design schema + endpoints"
  step 2: agent=data-engineer "write Prisma schema for users"
  step 3: agent=backend-dev   "implement CRUD routes"
  step 4: agent=tester        "write integration tests"
  step 5: agent=reviewer      "code review (read-only)"
  ↓
Each step → run via ReAct (Gemma) OR opencode (heavy lifting)
  ↓
Aggregated result → user
```

### Autonomous goal example

```bash
thmes goal add "monitor ~/Desktop/*.html daily and report any broken links" --schedule daily
thmes goal list
# 12 active goals
```

→ Background worker process picks goals from queue and runs them while user is away

### KPIs
- ✅ `/orchestrate "task"` plans 3-7 steps, executes, returns aggregated result
- ✅ Background goal completes overnight, notification on desktop
- ✅ Switch model mid-orchestration without losing context
- ✅ 10 autonomous goals running concurrently (queue-throttled)

---

## 🎨 TUI Refresh (Cross-cutting, ~8-12 hr)

### Why
Current rich+prompt_toolkit gives inline output — works but doesn't scale to multi-pane

### Target: Migrate to **Textual** framework

| Component | Current | Textual |
|---|---|---|
| Layout | Inline scrolling | True split panes (Vertical/Horizontal) |
| Header/Footer | Inline rules | Pinned via Header/Footer widgets |
| Streaming | Single block after generation | Live tokens via reactive text |
| Mouse | None | Click to copy, click to load skill |
| File picker | Path typing | DirectoryTree widget |
| Multi-session | None | Tabs |
| Theme | rich colors | CSS-like .tcss files |
| Notifications | Print | Toast pattern |

### Deliverables

| # | Task | Estimate |
|---|------|----------|
| T.1 | Textual app skeleton with header/footer/input | 2h |
| T.2 | Chat view (Markdown widget + auto-scroll) | 2h |
| T.3 | Live streaming output (token-by-token render) | 2h |
| T.4 | Monitor sidebar (stats, tool log, ctx bar) | 2h |
| T.5 | Session list sidebar (toggle with Tab) | 1h |
| T.6 | Keybindings: Ctrl+S save, Ctrl+L clear, F1 help | 1h |
| T.7 | Multi-modal attach via DirectoryTree dialog | 1h |
| T.8 | Theme: dark/light/dim | 1h |

### Optional UX wins
- 🔵 Mouse-clickable tool calls to expand/collapse
- 🟡 Auto-suggest from skill names while typing
- 🟢 Color-coded message roles (user/assistant/tool)
- 🟣 Inline "approve [y/n]" replaced with floating modal
- 🟠 Token-counter widget that updates as user types

---

## 📊 Effort Summary

| Phase | Estimate | Dependencies | Risk |
|---|---|---|---|
| Phase 1 (Foundation) | 6-10h | none | 🟢 low |
| TUI Refresh (Textual) | 8-12h | none (can run parallel) | 🟡 medium (UX impact) |
| Phase 2 (Intelligence) | 12-18h | Phase 1 | 🟡 medium (MCP integration) |
| Phase 3 (Autonomy) | 15-20h | Phase 2 | 🔴 higher (background process management) |
| **Total** | **41-60h** | | |

---

## 🚀 Suggested Execution Order

```
Week 1: Phase 1 (parallel TUI start)
  ├─ Day 1-2: Identity JSON + circuit breakers
  ├─ Day 3-4: SQLite sessions + resume
  └─ Day 5:   Tests + Textual scaffolding

Week 2: TUI Refresh complete + Phase 2 start
  ├─ Day 1-2: Textual main app
  ├─ Day 3-4: MCP integration
  └─ Day 5:   Memory tiers

Week 3: Phase 2 complete
  ├─ Day 1-2: Embedding memory
  ├─ Day 3:   Event bus + monitor pane
  └─ Day 4-5: Integration + tests

Week 4: Phase 3 part 1
  ├─ Day 1-3: L2 Orchestrator
  └─ Day 4-5: Step retry + review

Week 5: Phase 3 part 2
  ├─ Day 1-3: L3 Autonomous + goal queue
  ├─ Day 4:   Hot-swap registry
  └─ Day 5:   Final integration tests + docs
```

---

## ⚠️ Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Textual rewrite breaks existing UX | 🟡 medium | keep `thmes-classic` as fallback, opt-in to new TUI via flag |
| MCP servers slow startup | 🟢 low | lazy-load, only spawn when first tool call |
| Embedding model RAM cost | 🟡 medium | nomic-embed 4-bit ~200MB, manageable |
| Background worker zombie processes | 🔴 high | proper signal handling, PID file, watchdog |
| SQLite locking with concurrent goals | 🟡 medium | WAL mode + retry on busy |
| Gemma can't plan well (orchestrator) | 🔴 high | fallback to opencode for planning, Gemma for execution |

---

## 📦 Dependencies to install

```bash
~/.mlx-env/bin/pip install \
  prisma sqlalchemy             # Phase 1 (DB)
  mcp                            # Phase 2 (MCP protocol)
  sentence-transformers          # Phase 2 (embeddings — or use mlx)
  textual                        # TUI Refresh
  apscheduler                    # Phase 3 (background goals)
```

---

## 🎁 Deliverables when done

By v1.0:
- `thmes` TUI with Textual (multi-pane, mouse, themes)
- `gemma-cli` headless mode (`gemma-cli "task"` returns result)
- `thmes-daemon` background worker for autonomous goals
- `~/.thmes/` config dir with agents, skills config, mcp.json
- SQLite persistent state (~/.thmes/data.db)
- Documentation: `~/.thmes/README.md`, this ROADMAP
- Test suite: 50+ E2E tests, 100+ unit tests

---

## 🛡️ Shipped — Privacy relay (mask → cloud → unmask) · 2026-06-11

Cross-cutting feature so a strong **cloud** model can be used **without** sensitive
data leaving the machine. The local model is the trusted middle layer:

```
real prompt → [MASK · local]  replace PII/secrets with __PII_*__ + RAM vault
            → [LEAK-SCAN]      abort if any real value/secret would go out
            → [REASON · cloud] cloud sees placeholders only
            → [UNMASK · local] deterministic restore of real values
            → output
```

- Detection = **hybrid**: regex (email/phone/Thai-ID/card/API-key/.env/private-key/IP/
  path) + local-model NER (person/org/project) + user deny-list.
- Vault = **in-RAM, per-session** (never on disk, never to cloud); unmask is exact
  string-replace (no model → can't hallucinate a value back).
- `/relay on|off · tools on|off · model · cats · deny · vault · status`. Cloud model is
  smoke-tested on entry; failure kicks back to default local mode. Settings persist in
  `~/.thmes/data/relay.json`.
- Engine: `lib/thmes_mask.py`; glue + 3-stage pipeline in `bin/thmes` (see CODEMAP §2.10).
  Tests: `tests/test_r_relay.py` (49 checks).

### Agentic relay — cloud = brain, local = hands · 2026-06-18

Opt-in sub-mode (`/relay tools on`, flag `relay_tools`, default OFF). Extends the
one-shot relay into a **ReAct tool loop**: the cloud decides which tools to call
(read/write files, run shell/python, search), THIS machine executes them, and every
tool result is re-masked before it returns to the cloud. The masking boundary is
**symmetric** across the loop:

```
cloud (masked) ── decides ──▶ write_file(content="…__PII_PERSON_1__…")
              ◀── UNMASK args ── local exec (real path/content; approval shows REAL action)
              ── MASK result + leak_scan ──▶ cloud (placeholders only)   … repeat
final answer  ── UNMASK ──▶ user
```

- Vault accumulates across rounds → a value surfaced by `read_file` in round 1 keeps
  the same placeholder the cloud references in round 3.
- Tool-result leak policy = **redact-and-continue**: if a secret survives masking, the
  whole result is withheld from the cloud (the action already ran locally).
- `run_relay_agent_loop` in `bin/thmes` (CODEMAP §2.10); tunables `THMES_RELAY_MAX_ITERS`.

### Local-only relay — cloud = director, local = hands+eyes · 2026-06-22

Opt-in sub-mode (`/relay local on`, flag `relay_local`, default OFF; **precedence over
`relay_tools`**). The strictest privacy posture: where agentic relay sends *masked tool
results* up, local-only sends **no file content at all** — masked or not. The cloud is a
**director** that emits one plain-language step at a time and only reads a short,
content-free status line back; the LOCAL model does every read/edit/run on real data.

```
cloud (masked task) ── emits ──▶ "step: add a 30s timeout to the http client"
                    ◀── UNMASK step ── local agent_turn executes on REAL data (own history)
                    ── distil → ONE masked status line ──▶ cloud   … repeat until "DONE:"
DONE: summary ── UNMASK ──▶ user
```

- Solves the small-model gap: the local model often can't *plan* a multi-step task but
  can *carry out* a concrete instruction — cloud supplies reasoning, local supplies the
  hands+eyes, and file content never crosses the network.
- Status distiller (`_relay_local_status`) is itself a LOCAL pass told to omit code/content;
  masked + leak-scanned, with a generic fallback if anything risky survives.
- `run_relay_local_loop` in `bin/thmes` (CODEMAP §2.10); reuses `agent_turn` as the executor.

### Ollama-first default model · 2026-06-22

Startup now prefers an available Ollama model as the default when the user hasn't pinned
`THMES_MODEL` — Ollama is the primary backend on most machines and needs no MLX install.
The `DEFAULT_MODEL` constant is unchanged (sync-safe); only the startup *resolution*
adapts (`_THMES_MODEL_EXPLICIT` gate in `main()`). MLX-only machines (no Ollama) keep
their MLX default; an explicit `THMES_MODEL` always wins; a pinned-but-unloadable MLX
alias still falls back to Ollama. Verified across `gemma4:e2b/e4b` + `typhoon2.5` (100%
on a csv/xlsx/pptx read-and-answer eval).

### Router decides web-vs-local (no keyword regex) · 2026-06-22

A local question — "ตอนนี้ใน folder คุณเห็นไฟล์อะไรบ้าง" — used to launch a 92s web-research
loop because `_RESEARCH_TRIGGER_RE` matched the time word "ตอนนี้" and bypassed the router.
Reworked so the **LLM router decides**, not a regex:

- `ROUTER_PROMPT` emits a `web` bool; `smart_route` returns it. The keyword fast-path no
  longer short-circuits a web tool (defers ambiguous "ล่าสุด" to the LLM); an empty tool
  selection loads the full toolset instead of crippling the agent.
- Auto-research now fires only when **the router picked a web tool AND no local/file tool**
  (`_LOCAL_INTENT_TOOLS`) — so "ไฟล์ล่าสุด" → `[list_dir,bash,web_search]` reads as local
  (web_search stays as the agent's fallback), "ราคาทองวันนี้" → `[web_search]` reads as web.
  The standalone `web` bool is too noisy to trigger on (small models mislabel it, big models
  over-include web_search). Regex remains only as the no-router fallback.
- Validated by a **206-case TH/EN stress test** on the two router models: local categories
  ~100% on both; gemma4:e2b ~84% (residual misses are genuine 2B ambiguity on "X ล่าสุด"),
  typhoon2.5 web categories ~100%. Bigger router model = better ambiguous-case routing.

### Working directory (project root) · 2026-06-22

`thmes` now anchors all relative file work to a **project root** that defaults to the
directory it was launched from and is changeable at runtime (`/cd`, `/pwd`, or the
`set_workdir` tool). `_set_workdir` does `os.chdir` + updates the `_WORKDIR` global so
relative paths, grep globs, and shell/python children all resolve against the same root.
Pairs naturally with local-only relay (cloud says "work in project X" → local sets root).

---

*Roadmap v1.0 — generated 2026-05-13*
