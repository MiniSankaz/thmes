# CODEMAP — thmes source index

> **Purpose:** a navigation index so an AI/dev can jump straight to the right code
> without re-scanning all ~8.7k lines. Generated from a full skeleton scan on
> **2026-06-10**. Line numbers are *approximate* (they drift as code changes) —
> use them as a starting offset, then confirm with `grep -n 'def name'`.
>
> **Regenerate after big edits:**
> ```bash
> grep -nE '^class |^def |^[A-Z_][A-Z0-9_]* *=' bin/thmes
> grep -nE '^class |^def |^    def ' lib/*.py
> ```

---

## 0. Project status / naming

- The project was renamed **gemma-tui → thmes** (THMES-CLI). All binaries, modules,
  env vars, and the data home use the `thmes` name. A pre-existing `~/.gemma-tui/`
  data dir is **migrated to `~/.thmes/` automatically** on first run (see the data-home
  block in `bin/thmes`, and the same migration in `thmes-daemon` / `thmes-pro`).
- "gemma" now refers **only to the Gemma model** (`gemma` alias, `gemma4:e4b`,
  `bin/gemma`, `mlx-serve-gemma`) — never the project.
- Env vars are **`THMES_*`** (the legacy `GEMMA_TUI_*` fallback was removed). Data-home
  override: `THMES_HOME`. History file: **`~/.thmes-history`**. Tests live in `tests/` (§8).

---

## 1. Entry points (bin/)

| File | Lines | Role |
|---|---|---|
| **`bin/thmes`** | **5805** | THE core. Classic Rich + prompt_toolkit TUI. All shared symbols live here. |
| `bin/thmes-pro` | 1277 | Textual multi-pane UI. **Dynamically imports `thmes`** via `SourceFileLoader`. Monkey-patches tqdm→no-op before importing mlx_vlm. |
| `bin/thmes-daemon` | 234 | Background goal worker. Imports `thmes` + `lib/thmes_*`. Long-polls `goals.db`. |
| `bin/thmes-web` | ~25 | Launcher → `web/server.py`: serves the **thmes CLI in a browser** (PTY + WebSocket + xterm.js). Resolves its real path through the install symlink. See §10. |
| `bin/gemma` | 67 | One-shot text gen via mlx_vlm; `--server` = OpenAI-compatible HTTP :8081. |
| `bin/mlx-serve-{gemma,qwen,qwen3}` | 6–7 | Thin wrappers around `mlx_vlm.server` / `mlx_lm.server`. |
| `bin/hermes-use` | 20 | Point Hermes CLI at one of the mlx servers. |

**Cross-file contract:** `thmes-pro` and `thmes-daemon` reuse `TOOLS`, `ModelManager`,
`SessionStore`, `load_agents`, `MODELS`, `MODEL_CONTEXT`, `_FLAGS`, `DEFAULT_MODEL`
from `thmes`. **Changing any of those signatures requires updating both importers.**

---

## 2. `bin/thmes` map (by concern, with line offsets)

### 2.1 Model layer
| Symbol | Line | Notes |
|---|---|---|
| `class ModelProfile` | 161 | per-model traits (family, tool-prompt format, chunk size) |
| `_family_from_string` | 169 | name → (family, size-tag) |
| `_detect_model_profile` | 196 | builds ModelProfile from a ModelManager |
| `MODELS` / `MODEL_CONTEXT` | 103 / 109 | model registry + native context windows |
| `DEFAULT_MODEL` | 114 | env `THMES_MODEL`, default `qwen-vl` |
| `class ModelManager` | 3359 | loads/holds the MLX model+processor; `generate()` |
| Ollama helpers | 3281–3352 | `_ensure_ollama`, `discover_ollama_models`, `_is_ollama_alias` |
| **Ollama resilience** (added 2026-06-10) | after `_is_ollama_alias` | `_ollama_ps` (parse `/api/ps`→{tag:ctx}), `_ollama_resolve_ctx` (reuse loaded ctx → avoid reload), `_ollama_warmup` (1-token preload). Called from `mm.load()` Ollama path. |
| `_is_cloud_model(tag)` | before `_ollama_chat` | True for cloud tags — catches BOTH `':cloud'` (glm-4.6:cloud) and `'<size>-cloud'` (gpt-oss:120b-cloud, qwen3-coder:480b-cloud) by testing the segment after the final `:`. Used by `_ollama_chat` + `mm.load()` (banner/warmup-skip) + 401-hint. |
| `_ollama_tools_schema(tools_on)` | before `_ollama_chat` | builds Ollama **native function-calling** schema from enabled TOOLS (name/desc/params→JSON schema). `tools_on` dict→that subset, bool→full TOOLS. |
| `_native_tool_calls_to_text(tcs)` | before `_ollama_chat` | serializes native `message.tool_calls` → canonical `<tool_call>{...}</tool_call>` text so `parse_tool_calls()` handles native + text via one path. Unwraps llama3.2's `{type,value}` arg wrap. |
| `_ollama_chat(…, tools=None)` | ~3770 | chat via Ollama HTTP. **Native tool-calling**: when `tools` passed, sends `tools` schema + reads streamed `message.tool_calls` → folds into `<tool_call>` text (reliable across gpt-oss/qwen3-coder/glm/minimax/gemma). **Local**: num_ctx OOM ladder (500→halve). **Cloud** (`_is_cloud_model`): omit num_ctx, skip ladder, retry transient 500 ×3 → cloud error. **thinking-fallback**: empty `content` + non-empty `message.thinking` → use thinking. + timeout-retry. |
| `generate_reply(…, tools=None)` | 3745 | **unified generation entry** (MLX or Ollama), returns (text, stats). `tools` forwarded to Ollama native path only (MLX ignores). |

### 2.2 Agents & skills
| Symbol | Line | Notes |
|---|---|---|
| `load_agents` | 277 | prefers `~/.thmes/agents/`, falls back to `~/.claude/agents/*.md` |
| `_parse_fm` | 256 | YAML frontmatter parser for fallback agents |
| `load_skills` | 341 | scans `skills/*/SKILL.md` |
| `_parse_skill_phases` | 355 | phase block parser (tested in `test_skill_phase_parsing.py`) |
| `run_skill_agentic` | 368 | execute a skill as a multi-phase agent run |

### 2.3 Tools (the `TOOLS` dict + implementations)
| Symbol | Line | Notes |
|---|---|---|
| `TOOLS` dict | 1634 | name → {fn, params, desc}. **Single source of tool registry.** |
| `TOOL_RISK` | 469 | safe / ask per tool |
| `TOOL_RISK_TIER`, `_RISK_STYLE` | 484 / 493 | UI risk styling |
| `_DANGEROUS_BASH_RE` | 501 | extra-risk bash detection |
| File tools | 704–760 | `read_file` 704, `write_file` 708, `edit_file` 724, `delete_file` 745, `list_dir` 760 |
| **Document extraction** | before `read_file` | `read_file` auto-extracts Office formats to text so small models can read real-world files. `_extract_document(p)` routes by suffix: `.xlsx/.xlsm`→`_xlsx_to_text` (sheets→TSV), `.pptx`→`_pptx_to_text` (slide text), `.docx`→`_docx_to_text` (paragraphs); plain-text/code/CSV read verbatim; unknown binary → honest note (no mojibake). Each extractor tries the optional lib (`openpyxl`/`python-pptx`/`python-docx`) then a **stdlib `zipfile`+`xml.etree` fallback** (`_xml_localname_text` strips namespaces) → no-dependency install still works. All on-machine → composes with local-only relay. `_PLAINTEXT_SUFFIXES`, `_DOC_EXTRACTORS`. |
| `tool_grep` | 767 | |
| `tool_bash` | 781 | 30s timeout. **Trailing `&`** → detaches with DEVNULL fds + returns fast (no pipe hang on a backgrounded server). **Timeout** → clean message + hint to use `&`, not a raised exception. + `_suggest_install_hint` 803, `tool_install_dep` 833 |
| **Web tools** | | `tool_web_fetch` 1042, `tool_web_search` 1120 (DDGS, 5min cache) |
| HTML clean pipeline | 911–1040 | `_pre_strip_html`, trafilatura/bs4/regex extractors, `_looks_like_garbage` |
| `tool_python` | 1276 | sandboxed (`_PY_SAFE_MODULES` 1254, 10s timeout) |
| `tool_opencode` | 1355 | delegates to `~/.opencode/bin/opencode`; gated by `_FLAGS["opencode_enabled"]` |
| opencode maps | 1322–1339 | `OPENCODE_PRIMARY`, `OPENCODE_SUBAGENTS`, `SUBAGENT_PRIMARY_MAP` |
| datetime/path tools | 571 / 643 | `tool_current_datetime`, `tool_current_directory` |
| **Working dir (project root)** | 712–745 | `_WORKDIR` (global, = launch cwd) · `_set_workdir(path)` (validate dir → `os.chdir` + update global, keeps process cwd in lock-step) · `_resolve_path(path)` (relative paths hang off `_WORKDIR`; abs/`~` honoured) · `tool_set_workdir` (model-facing, risk `safe`). All file tools resolve via `_resolve_path`; `tool_bash` passes `cwd=str(_WORKDIR)`; `tool_python` runs in-process (inherits synced cwd). Slash: `/cd PATH`, `/pwd`. |
| `tool_ask_user` | 665 | interactive question tool |
| `tool_tasklist` | 1592 | in-TUI task list; `class TaskStore` 1479, `TASKS_DB` 1475 |
| **`tool_make_report`** | before `TOOLS` | **built-in report tool** (stdlib-only). Markdown → styled self-contained HTML (or `.md`) under `THMES_HOME/reports/`; open + ⌘P → PDF. Helpers: `_md_to_html` (headings/tables/fences/lists/quotes), `_md_inline`, `_REPORT_CSS`, `_REPORT_HTML`. Risk: `safe`. |

### 2.4 Tool-call parsing & salvage
| Symbol | Line | Notes |
|---|---|---|
| `parse_tool_calls` | 2281 | tolerant multi-strategy parser (6 strategies, see CLAUDE.md) |
| Parser regexes | 2213–2248 | `TOOL_CALL_RE`, `JSON_FENCE_RE`, `XML_FUNC_RE`, `GEMMA_CALL_RE`, `PY_CALL_RE`, Mistral/DeepSeek/Command-R, think/channel strippers |
| `_coerce_keys` | 2260 | `{function,args}`/`{tool,params}` → `{name,arguments}` |
| `has_suspicious_tool_attempt` | 2484 | detect a failed tool attempt to trigger correction |
| `salvage_file_writes` | 2428 | recover file content from broken JSON/heredoc/codeblock |
| Salvage regexes | 2392–2414 | `HEREDOC_RE`, `CODEBLOCK_RE`, `BROKEN_HEREDOC_RE`, `BROKEN_WRITE_RE` |

### 2.5 Router + prompt analysis (relevant to the research feature)
| Symbol | Line | Notes |
|---|---|---|
| `class PromptAnalysis` | 1965 | lang/domain/intent/time-sensitivity/topic + **`search_angles`** |
| `_analyze_prompt` | 1983 | <1ms heuristic; no LLM. Fills PromptAnalysis. |
| `_build_search_angles` | 2054 | **generates 3–4 query angles** (TH/EN/abbrev/broad) — REUSE for keyword expansion. **Forecast-aware**: if `_FORECAST_RE` fires on a finance query, swaps 2 spot-price angles for forward-looking ones (`แนวโน้มราคา X` / `X price forecast`) so synthesis gets analyst outlooks, not just spot. |
| `_FORECAST_RE` | ~2004 | forward-looking markers (แนวโน้ม/คาดการณ์/มีโอกาส/ฟื้นตัว/forecast/outlook/…) — distinct from `_PA_FACTUAL_RE` (current value). Drives forecast-aware angles. |
| `_extract_finance_entity` | 1975 | finance ticker/entity detect |
| PA regexes | 1887–1949 | finance/tech/news/health/factual/compare/explain/opinion/task/chat detectors |
| `smart_route` | 2716 | fast keyword path → LLM router fallback. Returns `{tools, agent, skills, added_by_keyword, fast_path, web}`. **Fast path skips when it matched ONLY a web tool** (`kw_has_web`) → defers the web-vs-local call to the LLM (a keyword like "ล่าสุด" is ambiguous: "ไฟล์ล่าสุด" local vs "ข่าวล่าสุด" web). Empty LLM tool selection → caller loads the FULL toolset (don't cripple the agent). |
| `_keyword_augment` | 2702 | regex → tool union; returns (augmented, added). **REUSE pattern for query expansion** |
| `TASK_KEYWORD_TOOLS` | 2637 | 13 (regex, [tools]) tuples (TH+EN) |
| `ROUTER_PROMPT` / `ROUTER_JSON_RE` | 2499 / 2532 | LLM router prompt + output extractor. **Emits a `web` bool** (does answering need current/external INTERNET info?) with TH+EN examples that "ไฟล์/commit/log ล่าสุด" is LOCAL even with a time word. (The web *trigger* uses tool-choice, not this bool — see §2.6.) |
| `_LOCAL_INTENT_TOOLS` | ~2575 | `{read_file, write_file, edit_file, delete_file, list_dir, grep, bash, python, current_directory, set_workdir, opencode, install_dep}` — if the router picks any of these, a co-selected `web_search` is just a fallback, NOT a web-research signal. |
| `_compact_index` | 2534 | compact tool/agent/skill index for router |
| `_detect_continuity` | 2585 | continue-vs-new-topic detection; `_CONTINUE_RE` 2566, `_NEW_TOPIC_RE` 2575 |

### 2.6 ★ Research subsystem — DETERMINISTIC CONTROLLER (rewritten 2026-06-10, see §7)
| Symbol | Line | Notes |
|---|---|---|
| **`run_research_loop(query, *, depth, max_rounds, …)`** | **4750** | THE controller. search → count unique domains → if `<depth`, expand keywords → search again. Stops on enough domains / 2 stagnant rounds / max_rounds. Calls `tool_web_search` **directly** (model-agnostic — no tool-call parsing). Returns `(answer, meta)`. |
| `_expand_keywords(query, tried, …)` | 4614 | LLM-first RELATED keyword expansion + heuristic fallback; dedups vs `tried` |
| `_synthesize_research(query, evidence, lang)` | 4679 | final cited answer over evidence; corpus bounded (`_SYNTH_CORPUS_BUDGET` 6000 / block 1400 / `_SYNTH_MAX_TOKENS` 1600) so small models finish in-timeout; degrades to digest on error |
| `_evidence_digest(query, evidence, lang)` | 4724 | model-free fallback: bullet list of sources when synthesis fails |
| `_run_and_present_research(...)` | 4842 | run controller + print + persist + append to history (shared by auto path) |
| `_detect_uncertainty(reply)` | 2607 | TH+EN knowledge-gap phrase detector on a DRAFT → triggers research. `_UNCERTAINTY_RE` 2588 |
| `_extract_domains(text)` | 1126 | pull unique domains from tool output (coverage measure). `_URL_IN_TEXT_RE` 1123 |
| `_RESEARCH_TRIGGER_RE` | 2569 | factual/current-info keyword trigger (TH+EN). **NO LONGER the primary decider** — it's only the FALLBACK for when the router didn't run (auto_load off). |
| **auto-research trigger (LLM-driven)** | main loop ~7997 | `research_triggered` now keys off the ROUTER's tool picks, not a regex: `_needs_web = (web_search/web_fetch picked) AND NOT (any `_LOCAL_INTENT_TOOLS` picked)`. So "ตอนนี้ใน folder เห็นไฟล์อะไร"→[list_dir]→local; "ราคาทองวันนี้"→[web_search]→web; "ไฟล์ล่าสุด"→[list_dir,bash,web_search]→local (web_search is a fallback the agent loop still has). The standalone `web` bool is intentionally NOT used to trigger (noisy: small models mislabel it, big models over-include web_search). Validated by a 206-case TH/EN stress test on e2b + typhoon2.5. |
| `/research` handler | 5559 | `/research QUERY [--depth N] [--rounds N]` and `/research auto on|off` → **uses `run_research_loop`** |
| auto-trigger sites | ~7997 (pre-emptive, router-driven), post-draft uncertainty block after quality-check | router says web → research before drafting; uncertain draft → research then rewrite |
| `_FLAGS` research keys | 216–230 | `research_auto`, `research_depth` (3), `research_rounds` (3), `research_kw_llm` (True). Env: `THMES_RESEARCH_{AUTO,DEPTH,ROUNDS,KW_LLM,CORPUS,ANSWER_TOKENS}` |
| `_research_system_block` / `_research_hint_block` | 3542 / 3616 | LEGACY prompt blocks — no longer the engine (controller replaced them); kept for reference/fallback |
| `_plan_system_block` / `_parse_plan_steps` / `_PLAN_TRIGGER_RE` | 3536 / 3551 / ~3524 | `/plan` mode; `_FLAGS["plan_auto"]` |

### 2.7 Agent loop (ReAct)
| Symbol | Line | Notes |
|---|---|---|
| **`agent_turn`** | **4162** | main loop `for it in range(max_iters)` (default 6, research 30). Parse→execute→feed back→repeat. Passes `_ollama_tools_schema(tools_on)` to `generate_reply` (native tool-calling). **Empty-turn nudge** (`MAX_EMPTY_NUDGES=2`): a turn with no content+no tool call mid-task → nudge to continue instead of ending on "". |
| Stop conditions | 4267 / 4354 / 4509 | no-calls return; stuck-detector break; max-iters synthesize |
| `MAX_CORRECTIONS` | 4174 | =2 format-correction retries |
| `MAX_ASK_USER` | 4199 | =3 |
| `DRIFT_NUDGE_EVERY` | 4185 | =3, re-states goal |
| `_run_safe_parallel` | 4110 | run safe tools concurrently |
| `execute_tool` | 3159 | single tool exec + approval defense-in-depth |
| approval helpers | 3007–3098 | `_tool_needs_approval`, `request_tool_approval`, `_action_summary`, `_call_fingerprint` |
| `class CircuitBreaker` / `_BREAKER` | 2932 / 2999 | per-tool breaker (threshold 3, cooldown 15s) |

### 2.8 Context / sessions / compaction
| Symbol | Line | Notes |
|---|---|---|
| `class SessionStore` | 2819 | WAL SQLite; sessions+messages; auto-title |
| `measure_context` | 3229 | tokens in/out vs native |
| `compact_history` | 3242 | summarize all but last `keep_recent=4` |
| `count_tokens` / `native_ctx` | 3222 / 3215 | |
| `COMPACT_THRESHOLD` | 116 | 0.6 (env `THMES_COMPACT_PCT`) |
| `tools_system_block` | 2176 | **builds the system prompt** (datetime, path, lang rule, tools JSON, skills); `TOOL_PROMPT_BY_FAMILY` / template 1759–1872 |
| `_quality_check` | 2135 | post-reply quality heuristic |

### 2.9 UI / input plumbing
| Symbol | Line | Notes |
|---|---|---|
| `main` | 4738 | the REPL loop; all slash-command dispatch lives here |
| `render_header` / `make_bottom_toolbar` | 4663 / 4707 | header + toolbar (context color-coding) |
| `banner` / `help_panel` / `list_panel` | 4543 / 4617 / 4654 | |
| `_model_picker` | 4550 | startup model picker (Ollama+MLX) |
| ESC / queue | 3832–4044 | `_EscCancelGuard`, `with_esc_cancel`, `_QueueListener`, `drain_queue` (`QUEUE_ENABLED` 3956) |
| tool spinner | 4070–4108 | `_format_tool_status`, `_start_tool_spinner` |
| `ask_yn` | 54 | y/n prompt w/ "always" memory |
| `CMD_META` | ~4789 | slash-command metadata for `SlashCompleter` (~4827) — **register new commands here too** |

### 2.10 ★ Privacy relay — mask (local) → reason (cloud) → unmask (local) (added 2026-06-11)
> Goal: use a strong cloud model **without** sensitive data ever leaving the machine.
> Local model masks → cloud reasons on placeholders only → local restores real values.
> Masking engine = `lib/thmes_mask.py` (§3). Grep symbols (line offsets drift):

| Symbol | Notes |
|---|---|
| `_ollama_chat(…, model=, ctx=, temperature=, think=)` | **cloud override**: call any Ollama/cloud model WITHOUT swapping the loaded local `mm` (refactored the 6 `mm.ollama_meta` refs → `_model`/`_ctx`). `temperature` (relay NER uses 0 → deterministic) + `think` (payload `think:false` → thinking clouds glm/gpt-oss return the answer, not the CoT) thread through. |
| `generate_reply(…, model=)` | if `model` set → forces the `_ollama_chat` path regardless of `mm.backend` (cloud over HTTP, no local RAM). |
| `run_mask_pipeline(history, *, cloud_model, vault, max_tokens, ner_fn, agent_system, gather_files=True)` | controller: **build-data** (`_relay_gather_files` reads local files the msg references) → mask payload (NER on latest user msg only) → **leak_scan guard** (abort if a real value/secret would go out) → cloud REASON (`think=False`) → `vault.unmask`. Returns `(final, meta)`; `final=None` on leak/cloud abort → caller falls back to local. |
| `_relay_gather_files(text)` | read-only, size-capped read of `~?/…` paths in the latest message → so the cloud can report on a file; content is masked like everything else. |
| `_run_and_present_mask` | run + 3-stage banner + persist (stores UNMASKED to local session) + counts-only summary. |
| `_relay_ner` | local-model NER wrapper (`NER_PROMPT`→`parse_ner`); runs on `mm` at `temperature=0, think=False, max_tokens=1536` (gemma is a reasoning model — needs headroom + no CoT so the JSON lands), best-effort. |
| `_enter_relay_mode` / `_cloud_smoke_test` / `_pick_cloud_model` / `_discover_cloud_models` / `_resolve_relay_cloud` | mode entry: resolve/pick cloud → smoke-test → on+persist, else **kick back to default**. Refuses if active model is itself cloud. |
| `_relay_ensure_vault(session_id)` | one MaskVault per session; auto-clears on session switch (vault never crosses sessions). |
| `_relay_settings_load/_save` | persist `cloud_model`/`deny_list`/`groups` → `THMES_HOME/data/relay.json` (bin/thmes stays lib-import-free except the soft `thmes_mask` import). |
| main-loop hook | `if _FLAGS["relay_mode"]:` block **before** `research_triggered` — takes precedence, `continue`s on success, falls through to local `agent_turn` on abort. **3-way branch:** `relay_local` → `_run_and_present_relay_local` (local-only, precedence), elif `relay_tools` → `_run_and_present_relay_agent` (agentic), else → `_run_and_present_mask` (one-shot). |
| `_RELAY_SYS` | cloud system prompt: "copy `__PII_*__` placeholders verbatim, never alter". |

### ★★ Agentic relay (sub-mode, added 2026-06-18) — cloud = brain, local = hands
> Opt-in via `/relay tools on` (flag `relay_tools`, default OFF). When ON, relay drives
> a ReAct **tool loop**: the cloud decides the calls (seeing only placeholders), THIS
> machine executes them, and every tool result is re-masked before it returns to the
> cloud. The symmetry is the trick: **cloud→local UNMASK the call args** (exec needs
> real values), **local→cloud MASK the result** (raw PII never leaves).

| Symbol | Notes |
|---|---|
| `run_relay_agent_loop(history, *, cloud_model, vault, tools_on, allow_dangerous, max_tokens, ner_fn, agent_system, max_iters, gather_files, on_event)` | THE agentic controller. Masks the starting payload → leak-guard → loop: `generate_reply(model=cloud, tools=schema, think=False)` → `parse_tool_calls` → for each call `_relay_unmask_args` → `execute_tool` (real args, real approval) → `_relay_mask_result` → feed `<tool_result>` back. Vault accumulates across rounds (consistent placeholders). Returns `(final, meta)`; `final=None` on initial leak / first-round cloud fail → caller falls back local. After `max_iters`, one tools-free synthesis round. Schema gating does NOT depend on `mm.backend` (cloud always over Ollama HTTP via `model=`). **Empty-turn nudge** (`MAX_EMPTY_NUDGES=3`): a stall (`""`, NOT `[ollama …]`) mid-chain → inject a `(continue)` nudge instead of aborting the tool chain (small models stall mid-task; mirrors `agent_turn`). **Action-narration nudge** (`MAX_ACTION_NUDGES=3`, `_RELAY_PLANNING_RE`): a no-tool-call turn whose text reads like an unfinished plan ("we need to write …", "จะเขียน") → nudge to EMIT the call instead of accepting the narration as the final answer — stops thinking cloud models (gpt-oss/qwen3-coder) from ending a multi-step read→process→write task after just narrating the next step. |
| `_relay_unmask_args(value, vault)` | recursively restore placeholders in a cloud-issued call's args (nested dict/list) so LOCAL exec uses real path/content/command. |
| `_relay_mask_result(result, vault, *, run_ner)` | re-mask a tool result + leak_scan; if a high-risk secret survives masking → **redact whole result** (work already ran locally, cloud just doesn't see raw output). Returns `(safe_text, redacted_bool)`. NER only on `_RELAY_NER_RESULT_TOOLS` (read/grep/list/web_*). |
| `_run_and_present_relay_agent` | presenter: run loop + per-tool banner (`on_event`) + persist UNMASKED to local session + counts/tool-calls/iters/redacted summary. |
| `_RELAY_TOOLS_SYS` | system-prompt addendum (only in agentic mode): "you may call tools; keep placeholders verbatim in ARGS too; machine restores before running". |
| `_RELAY_NER_RESULT_TOOLS` | `{read_file, grep, list_dir, web_fetch, web_search}` — run local NER when re-masking these (free-form text); bash/python skip it (structured; rules+leak_scan cover). |

### ★ Self-heal — verify → LOCAL triage → re-ask cloud (added 2026-06-19)
> Opt-in per session via `/relay verify <cmd>`. After the agentic loop, the verify
> command runs locally; on failure the LOCAL model triages the raw error and the
> (masked) error+diagnosis is fed back to the cloud to fix — looping up to
> `relay_heal_attempts`. local = hands+eyes (runs code, sees real stack traces, triages);
> cloud = brain (fixes). Privacy-preserving: triage sees raw values, only a masked
> diagnosis goes up. **Design note:** the local diagnosis is a HINT — the raw error is
> ALWAYS sent too, so a wrong local fix-direction (a 4B *and* a 30B both mis-read the
> misleading websockets `missing 'path'` error in testing) still heals because the cloud
> reasons over the raw error.

| Symbol | Notes |
|---|---|
| `run_relay_selfheal(history, *, …, verify_cmd, heal_attempts, on_attempt)` | wraps `run_relay_agent_loop` in the verify/triage loop; heal turns live in a private history copy (don't pollute the session). Returns `(final, meta)` with `meta['attempt']`/`['verify_ok']`. |
| `_relay_triage(raw_error)` | LOCAL model (`mm`, no cloud) distills a 2-3 line diagnosis from the REAL error. Best-effort. Prompt `_RELAY_TRIAGE_PROMPT`. |
| `_relay_run_verify(cmd, timeout=90)` | run the user's verify command (`shell=True`), return `(passed, output)`. |
| `_relay_heal_prompt(raw, diag)` | the follow-up turn fed back to the cloud (raw error + diagnosis-as-hint); masked by the relay before it's sent. |
| `/relay verify <cmd>\|off` + status | session flag `relay_verify_cmd` (never persists), `relay_heal_attempts` (3). Presenter `_run_and_present_relay_agent` calls `run_relay_selfheal` when a verify cmd is set, else `run_relay_agent_loop`. |

**Invariants (enforced + tested):** real vault values never reach the cloud — even in
tool ARGS (cloud emits placeholders, local unmasks just-in-time) and tool RESULTS
(re-masked before return; unmaskable secret → redacted) · approval prompt shows the
REAL action (informed consent) · whole payload masked (system+history) · unmask is
deterministic exact-replace · leak-scan runs ALL rules even for disabled groups · vault
in-RAM/session-scoped, never on disk · UI shows counts+categories, real values only
behind `relay_show_values`/`-v`.

### ★★ Local-only relay (sub-mode, added 2026-06-22) — cloud = DIRECTOR, local = hands+eyes
> Opt-in via `/relay local on` (flag `relay_local`, default OFF; **precedence over
> `relay_tools`** in the main-loop hook). Strongest privacy posture: unlike agentic relay
> (masked tool RESULTS go to the cloud), here **no file content reaches the cloud at all —
> not even masked**. The cloud emits ONE plain-text step at a time and only ever reads a
> short, content-free status line back; the LOCAL model (`mm`) does every read/edit/run on
> REAL data via `agent_turn`. Use when the local model can EXECUTE concrete steps but can't
> PLAN well — cloud supplies reasoning, local supplies the hands+eyes.

| Symbol | Notes |
|---|---|
| `run_relay_local_loop(history, *, cloud_model, vault, tools_on, allow_dangerous, max_tokens, ner_fn, agent_system, max_iters, on_event)` | THE local-only controller. Mask the task → leak-guard (only the masked task + planner sys ever leave) → loop: cloud `generate_reply(model=cloud, no tools)` emits one directive → `DONE:`-prefixed ⇒ unmask+return; else `vault.unmask` the directive → `agent_turn` runs it locally on real data (own running `local_history`, never sent up) → `_relay_local_status` distils a masked one-liner back to cloud. After `max_iters`, one final director turn for a `DONE:` summary. Returns `(final, meta)`; `final=None` on initial leak / first-round cloud fail → caller falls back local. |
| `_relay_local_status(local_reply, vault, *, ner_fn)` | LOCAL model distils the (long, content-bearing) executor reply → ONE abstract status line (`_RELAY_LOCAL_STATUS_PROMPT`), then mask + leak_scan; any risky survivor → generic "[kept on-machine]" marker so no content rides up inside the status. |
| `_RELAY_LOCAL_SYS` | director system-prompt: "you NEVER see file contents, only status reports; emit one imperative step, or a `DONE:` line when complete; never ask for contents; keep placeholders verbatim". |
| `_run_and_present_relay_local` | presenter: run loop + per-step/status banner (`on_event`) + persist UNMASKED summary to local session + steps/local-tool-calls/masked-counts summary. |

---

## 3. `lib/` modules

### `lib/thmes_orchestrator.py` (317) — L2 plan-then-execute
- `class OrchestrationStore` (62) → `orchestration.db`: create/update run+steps
- `parse_plan` (158): planner reply → step list
- `class Orchestrator` (183): `plan()` 208, `run(goal, with_review)` 220. Executors→opencode, others→inline ReAct, failed steps retry.

### `lib/thmes_goals.py` (239) — L3 autonomous queue
- `class GoalQueue` (35) → `goals.db`: `add` 71, `claim_next` 94 (atomic `UPDATE…RETURNING`), `mark_done` 120, `maybe_retry` 129, `stats` 160. Priorities critical/high/normal/low, FIFO per tier.
- `class GoalWorker` (171): `run_one` 196, `loop` 225 (long-poll).

### `lib/thmes_registry.py` (131) — hot-swap KV
- `class Registry` (29) → `registry.db`, 1s read cache. `current_model`/`set_current_model` 106/109, `role_model` 112. `get_registry()` singleton 127. Daemon calls `maybe_hotswap()` between goals.

### `lib/thmes_memory.py` (274) — L1–L4 memory
- `class EmbeddingEngine` (33): lazy `nomicai-modernbert-embed-base-4bit`, mean-pool.
- `class MemoryService` (95) → `memory.db` (FTS5 + float32 BLOB embeddings): `store` 133, `recall_by_key` 172, `recall_fts` 180, `recall_semantic` 202 (Python cosine). `_cosine`/`_f32_bytes` 90/81.

### `lib/thmes_mcp.py` (166) — MCP client
- `class MCPManager` (38): `load_config` 51 (`~/.thmes/mcp.json`), `list_tools` 115.
- `class SyncMCPClient` (126): sync wrapper, `call` 154.

### `lib/builtin_mcp_server.py` (84) — inverse MCP
- Exposes thmes `TOOLS` as an MCP server. `_find_core_bin` 23.

### `lib/thmes_notify.py` (73) — macOS notifications
- `send` 26, `notify_done` 45, `notify_goal_done` 58, `notify_orchestration_done` 67.

### `lib/thmes_mask.py` — ★ Privacy-relay masking engine (added 2026-06-11)
Pure, MLX-free, unit-testable. Powers the `/relay` privacy proxy (see §2.10).
- `class MaskVault` — session-scoped, **in-memory only** (never disk, never cloud).
  `mask(text, ner_fn=)` (rule + deny-list + injected NER, longest-first, belt-and-
  suspenders re-apply of known values) · `unmask(text)` (deterministic exact-replace,
  longest-token-first + tolerant `__PII_*__` fallback) · `leak_scan(text)` (real-value
  + **all-rules** secret check → defence-in-depth even for disabled groups) ·
  `stats()`/`mapping()`/`clear()`.
- `RULE_SPECS`/`_COMPILED` — email · phone · Thai-ID(checksum) · card(Luhn) · bank-account · US/intl phone · US-SSN · labeled IDs (HN/AN/employee/case) · court names · API-key ·
  `.env` secret(value-group) · private-key block · IPv4 · home path. `GROUP_LABELS`
  maps the 4 toggle groups (email/secret/person/net) → fine labels.
- `NER_PROMPT` + `parse_ner(reply)` — contextual person/org/project tagger (model-driven;
  parse grabs the LAST JSON array so a reasoning preamble doesn't break it). Prompt tags
  role-introduced names ("advisor/partner/client/ที่ปรึกษา <Name>") + a few-shot example —
  lifted dense-business-doc NER recall 84%→100% (gemma was dropping the advisor firm).
- **deny-list matching is whitespace/zero-width/case tolerant** (`_deny_rx`, `_DENY_SEP`):
  a listed term still matches "Project  Phoenix" / "project phoenix" / "สำนั ก งาน" (PDF
  intra-char spacing) — the ACTUAL span is masked, never the canonical form.
- PERSON entities also vault each significant **name part** (`_NAME_STOP` skips titles) so a
  later first-name-only reference doesn't leak.
- **Reliability:** rule categories are deterministic & exhaustive; NER is best-effort. For
  any must-never-leak name, the **deny-list** is the guaranteed, variant-tolerant path.
  Validated by a rotating-seed harness (5 dims incl. business-confidential): 100% across seeds.
- Placeholder = `__PII_{LABEL}_{N}__`. Tests: `tests/test_r_relay.py` (56 checks — Rr6 agentic, Rr7 self-heal
  covers the agentic loop: unmasked tool args, re-masked results, redaction).

---

## 4. Agents (agents/<name>/, 14 agents × 4 JSON files)

Each bundle = **5 files**: `identity.json`, `capabilities.json`, `safeguards.json`,
`config.json`, `system-prompt.txt` (verified — all 14 dirs have exactly 5).
`load_agents()` silently skips a dir if any of the 5 is missing/invalid JSON.
Agents: analyst, architect, backend-dev, ctx-manager, data-engineer, debugger,
doc-writer, financial, frontend-dev, git-ops, ops, research, reviewer, tester.
Loaded by `load_agents()` (thmes:277), prefers `~/.thmes/agents/`.

---

## 5. Slash commands (dispatched in `main()`, bin/thmes)

| Command | Line | Command | Line |
|---|---|---|---|
| `/quit` `/exit` | 4943 | `/queue` | 5320 |
| `/help` | 4952 | `/verbose` | 5355 |
| `/clear` | 4953 | `/opencode` | 5366 |
| `/image` | 4957 | `/context` | 5377 |
| `/audio` | 4961 | `/compact` | 5401 |
| `/agent` | 4966 | `/auto` | 5425 |
| `/skill` | 4975 | `/task` `/tasks` | 5437 |
| `/tool` | 4993 | `/continuity` | 5467 |
| `/model` | 5013 | `/system` | 5481 |
| `/session` | 5044 | `/max` | 5485 |
| `/breakers` | 5100 | `/save` | 5489 |
| `/plan` | 5121 | `/load` | 5493 |
| **`/research`** | **5228** | `/stats` | 5498 |
| **`/relay`** | (near `/research`) | — | — |

`/relay` subcommands: `on` (smoke-test cloud → enter) · `off` · **`tools on|off`**
(toggle agentic sub-mode — cloud decides tool calls, local executes) · **`verify <cmd>|off`**
(self-heal: run cmd after the loop → local triage → re-ask cloud) · `model [TAG]`
(set+persist+smoke) · `cats a,b` · `deny add|rm TERM` · `vault [-v]` · `status`
(the "Settings" view). Grep `cmd == "/relay"` for the exact line.

**To add a command:** dispatch `if cmd == "/foo"` in `main()` **and** add a `CMD_META`
entry (~4789) so tab-completion works.

---

## 6. Constants, flags, env vars

**`_FLAGS` dict (line 209):** `opencode_enabled`, `research_auto` (default ON),
`plan_auto` (default ON), `research_depth`/`research_rounds`/`research_kw_llm`,
`ollama_warmup` (default ON), `auto_load`,
`relay_mode` (default OFF, never persists), `relay_reason_tokens`,
`relay_show_values`, **`relay_tools`** (agentic sub-mode, default OFF, env
`THMES_RELAY_TOOLS`), **`relay_max_iters`** (6, env `THMES_RELAY_MAX_ITERS`),
**`relay_verify_cmd`** (self-heal verify cmd, session-only/never persists, env
`THMES_RELAY_VERIFY`), **`relay_heal_attempts`** (3, env `THMES_RELAY_HEAL_ATTEMPTS`),
… toggled via slash commands. Relay's persisted settings
(`cloud_model`/`deny_list`/`groups`) live in `THMES_HOME/data/relay.json`, not `_FLAGS`.

**Env vars (read at module load via `_env()`):**
`THMES_MODEL`, `THMES_MAX_TOKENS`, `THMES_COMPACT_PCT`,
`THMES_OPENCODE`, `THMES_VERBOSE`, `THMES_RESEARCH_AUTO`,
`THMES_PLAN_AUTO`, `THMES_CONTINUITY`, `THMES_QUEUE`, `THMES_DATETIME_AWARE`,
`THMES_PATH_AWARE`, `THMES_SKILLS_DIR`, `THMES_OLLAMA_HOST/TIMEOUT/API_KEY/NUM_CTX`,
`THMES_OLLAMA_LOAD_TIMEOUT` (180), `THMES_OLLAMA_WARMUP` (1),
`THMES_RESEARCH_{DEPTH,ROUNDS,KW_LLM,CORPUS,ANSWER_TOKENS}`,
`THMES_RELAY_{CLOUD,REASON_TOKENS,SHOW_VALUES,TOOLS,MAX_ITERS,VERIFY,HEAL_ATTEMPTS}`,
**`THMES_HOME`** (data home override).

**Key numeric constants:** `COMPACT_THRESHOLD=0.6`, `MAX_CORRECTIONS=2`,
`MAX_ASK_USER=3`, `DRIFT_NUDGE_EVERY=3`, breaker `threshold=3`/`cooldown=15s`,
web cache `300s`/`64` entries, research hard ceiling `30` tool calls,
`/research` default `depth=3`.

---

## 7. ★ Research subsystem — deterministic controller (implemented 2026-06-10)

Replaced the old prompt-only approach (which just *told* the model to keep
searching and relied on its judgment) with a **deterministic controller** that owns
the loop. Works the same across models because it calls `tool_web_search` directly —
it never depends on the model emitting valid tool-call syntax. The model is used for
only three judgment tasks: drafting, proposing keywords, and final synthesis.

**The loop — `run_research_loop` (4750):**
1. Start with `analysis.search_angles` (TH/EN/abbrev/broad).
2. Each round: run the batch of queries (`tool_web_search`, `auto_fetch` on the first
   query of the round), accumulate evidence, count unique source **domains**.
3. If `domains ≥ depth` → stop. If a round adds **0** new domains twice → stop
   (stagnation guard). Else `_expand_keywords` (LLM-first + heuristic) proposes NEW
   related queries (deduped vs everything tried) → next round.
4. `max_rounds` caps it. Then `_synthesize_research` writes a cited answer over the
   bounded evidence corpus; on model error it degrades to `_evidence_digest`.

**Three entry paths, all → `run_research_loop`:**
1. **Explicit** `/research QUERY [--depth N] [--rounds N]` (handler 5559).
2. **Pre-emptive auto** (~7997): **router-driven** — fires when the LLM router picked a
   web tool (`web_search`/`web_fetch`) and NO local/file tool (`_LOCAL_INTENT_TOOLS`) →
   research immediately (skip drafting from stale memory). `_RESEARCH_TRIGGER_RE` is only
   the fallback when the router didn't run. (Was a pure keyword regex pre-2026-06-22;
   changed so a local "ไฟล์ล่าสุด" isn't forced to web by the word "ล่าสุด".)
3. **Uncertain-draft auto** (post-quality-check block): model drafts → if
   `_detect_uncertainty(reply)` fires (no tool calls, factual intent) → research and
   rewrite the answer. This is the "ถ้าไม่รู้ → ไปค้นก่อน" mechanism.

All auto paths gated by `_FLAGS["research_auto"]` (`/research auto on|off`), skipped
for agents/custom-system/tool-result continuations/code·task·chat intents.

**Tuning** (`_FLAGS` + env): `research_depth` (3), `research_rounds` (3),
`research_kw_llm` (use model for keyword expansion; off = pure heuristic),
`THMES_RESEARCH_CORPUS` (synthesis input budget, 6000),
`THMES_RESEARCH_ANSWER_TOKENS` (1600).

**Perf note (auto-handled since 2026-06-10):** synthesis is one `generate_reply`
call (~10–13s on gemma4:e4b warm). The old "different `num_ctx` → 12GB reload →
timeout" trap is now handled by the **Ollama resilience layer** (§2.1): `mm.load()`
calls `_ollama_resolve_ctx` (reuse the resident model's ctx — no reload) then
`_ollama_warmup` (preload at our ctx); `_ollama_chat` retries once on timeout with
`OLLAMA_LOAD_TIMEOUT`. No manual `THMES_OLLAMA_NUM_CTX` needed in normal use.

Tests: `tests/test_r_research_loop.py` (27 — uncertainty, domains, keyword
expansion, loop, synthesis fallback) + `tests/test_r_provider.py` (7 — ctx
adaptation) + `_ollama_chat` timeout-retry in `test_r_behavioral.py` Rc4. See
`docs/ROADMAP.md`.

---

## 8. Tests (tests/ — exists despite CLAUDE.md saying otherwise)

**`_r_` = regression** (NOT research). Tests EXECUTE real functions, not grep source.

| File | Lines | Covers |
|---|---|---|
| `test_e2e_tui.py` | 463 | real tmux-driven E2E: startup, /help, /skill, /model, /sessions, /breakers (uses ol:gemma4:e4b) |
| `test_r_behavioral.py` | 595 | behavioral regression: `_parse_skill_phases`, `_PKG_SAFE_RE`, `tool_install_dep`, `_ollama_chat` retry, `CLAUDE_SKILLS` fallback |
| `test_r_dimensions.py` | 272 | multi-dimension regression of the same areas (regex/phase/install/ollama/paths) |
| `test_c_skill_handler.py` | 285 | skill handler (`jobs-to-tasks` etc.) |
| `test_skill_phase_parsing.py` | 335 | `_parse_skill_phases` |
| `test_r_research_loop.py` | — | research controller: `_detect_uncertainty`, `_extract_domains`, `_expand_keywords`, `run_research_loop`, synthesis fallback (27 checks) |
| `test_r_provider.py` | — | Ollama ctx-adaptation: `_ollama_ps`, `_ollama_resolve_ctx` (7 checks) |
| `test_r_tools.py` | — | mutating/ask-risk tools EXECUTED vs /tmp sandbox: write/edit/delete/bash(+background detach)/python(sandbox)/read/list/grep + cross-user-home security + make_report (36 checks) |
| `test_r_relay.py` | — | ★ privacy relay: MaskVault + leak_scan + NER + `_ollama_chat(model=)` + `run_mask_pipeline`, **Rr6 agentic `run_relay_agent_loop`** (args unmasked · results re-masked · redaction · empty-turn nudge), **Rr7 self-heal `run_relay_selfheal`** (`_relay_run_verify` pass/fail · heal prompt · verify→triage→re-ask loop · single-attempt when verify passes) (56 checks) |

Test harness auto-detects the binary: `THMES_BIN` env → `bin/thmes` → `bin/thmes`.
Full suite green as of 2026-06-19: 123+69+83+19+27+12+36+56 checks pass.
(`test_r_behavioral` Rc4-C0..C5 cover the cloud `_ollama_chat` path: `_is_cloud_model`
suffix detection, no-num_ctx for cloud, transient-500 retry, cloud-vs-RAM error.)

Run with the MLX venv python, e.g. `~/.mlx-env/bin/python -m pytest tests/` (no
configured runner; plain pytest/unittest files).

---

## 9. Runtime data (`~/.thmes/`, auto-created)

`data/sessions.db` (sessions+messages) · `data/memory.db` (L2–L4 + embeddings) ·
`data/goals.db` (queue) · `data/orchestration.db` (runs/steps) ·
`data/registry.db` (hot-swap KV) · `data/tasks.db` (in-TUI task list) · `reports/` (make_report HTML/MD output) ·
`data/daemon.pid` + `daemon.log` · `mcp.json` (optional) · `~/.thmes-history`.

---

## 10. `web/` — THMES Web Terminal (added 2026-06-19)

A browser front-end for the **`thmes` CLI itself** (not a model-API client): it spawns
the real `thmes` REPL in a PTY and bridges it to xterm.js over a WebSocket, so the full
CLI (routing, tools, sessions, slash commands, relay) runs in a browser tab — locally,
nothing leaves the machine.

| File | Notes |
|---|---|
| `web/server.py` | PTY + WebSocket bridge + static http.server. `_thmes_cmd()` resolves the CLI portably (`$THMES_CMD` → `thmes` on PATH → `../bin/thmes`). **Single-reader bridge** (`loop.add_reader` + one non-blocking read per event — no duplicate reader tasks). Ports: `THMES_WEB_HTTP_PORT` 8765 / `THMES_WEB_WS_PORT` 8766. |
| `web/index.html` | xterm.js (CDN) + FitAddon; connects `ws://<host>:8766`. **Generated by thmes in relay mode** during dev; backend productionised for the repo. |
| `web/README.md` | run + config + origin. |
| `bin/thmes-web` | launcher (`THMES_WEB_PYTHON` override; needs `pip install websockets`). |

Run: `pip install websockets && thmes-web` → open `http://localhost:8765` → Enter at the
model picker → use thmes normally. Verified E2E in a headless browser (banner streams,
`/help` executes live). Origin/provenance: this is the worked example of the agentic
relay + self-heal — the frontend was written by the model, the backend hardened by hand.

---

*Generated 2026-06-10. Re-run the grep commands at the top after structural edits and
update the affected line offsets.*
