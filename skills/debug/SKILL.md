---
name: debug
description: >
  This skill should be used when the user asks to "debug an error", "fix a bug",
  "investigate a failure", "troubleshoot an issue", or needs a structured 4-phase bug fix
  cycle (pre-analyze → investigate+fix → regression test → review+commit).
version: 1.2.0
type: workflow
triggers:
  keywords_en: [debug, bug, fix, error, troubleshoot, root cause, investigate failure]
  keywords_th: [แก้ไข, บัค, แก้บัค, ตรวจสอบข้อผิดพลาด, หาสาเหตุ]
verbs:
  - name: run
    purpose: Execute the 4-phase fix cycle (pre-analyze → investigate+fix → regression → review+commit)
    inputs: [error_description]
    outputs: text+files
required_tools: [Bash, Edit, Read, Grep]
related_skills:
  - coord: claim a coord thread for the cycle
  - track: register the bug as a task before Phase 1
  - review: Phase 3 reviewer overlaps with /review skill
  - implement: chain into /implement if fix requires new functionality
related_agents:
  - debugger: Phase 1 investigate+fix (sonnet)
  - tester: Phase 2 regression (sonnet)
  - reviewer: Phase 3 review (sonnet, READ-ONLY)
  - git-ops: Phase 3 commit (haiku)
---

# /debug — Bug Fix Cycle

> Workflow skill that drives a structured fix through 4 phases. Phase 0 uses local LLM
> (zero API cost) for triage; subsequent phases delegate to specialised subagents.
> Includes a fast path when debugger already wrote the regression test.

## When to invoke

- User reports an error or stack trace
- A test is failing and the cause needs RCA
- Production logs show an anomaly that needs reproduction + fix
- Need a regression test to lock in a fix

## When NOT to invoke

- Greenfield feature → use `/implement` instead
- Refactor without a known bug → use `/refactor`
- Performance issue → use `/performance` (different signal/methodology)
- Security finding → use `/security-audit` first to scope, then `/debug` per finding

## Verbs (detailed)

### `/debug <error description or bug report>` — run the cycle

**Input**: `<error_description>` — error message, stack trace, or short description.
**Output**: text — phase log + final commit.
**Side effects**:
- Creates coord thread covering the cycle
- Edits files in target paths
- Adds regression test(s)
- Final commit on working branch

## Phase workflow

### Phase 0: PRE-ANALYZE (local LLM + KG pre-search — zero API cost)

**0a) KG pre-search** (Pattern 5, 2026-05-07): query KG for relevant entities before spawning. Closes the context-asymmetry gap where main session's prompt.engine already enriched its own context but spawned subagents started cold.

```bash
KG_CONTEXT=$(curl -s -H "Authorization: Bearer $DAEMON_CORE_API_KEY" \
  "http://127.0.0.1:9991/api/kg/search?q=$(printf %s "$ERROR_TEXT" | jq -sRr @uri)&limit=8" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('items', [])[:8]
lines = []
for it in items:
    desc = (it.get('description') or '')[:80]
    line = f\"- [{it['kind']}] {it.get('namespace','')}:{it['name']}\"
    if desc: line += f' — {desc}'
    lines.append(line)
out = '\n'.join(lines)
print(out[:1500])  # cap to avoid prompt bloat
")
```

**0b) Local LLM analysis**:
```bash
ANALYSIS=$(llm-query "Analyze this error and suggest likely causes: {error_text}" --model general --format json)
```

Both `KG_CONTEXT` and `ANALYSIS` are passed to Phase 1's Task(debugger) prompt.

### Phase 1: INVESTIGATE + FIX

```
Task(debugger, "
  Investigate and fix:
  Error: {error_description}

  Pre-analysis hints (from local LLM):
  {local_llm_analysis}

  Context from KG (relevant Memory + Standard + prior fixes):
  {KG_CONTEXT}

  Context from previous step: {any accumulated context}

  Follow Debug Process:
  1. Reproduce → 2. Dependency Analysis → 3. Impact Analysis
  4. Root Cause Analysis → 5. Implement Fix → 6. Create Regression Test
")
```

Parse debugger's CHAIN_OUTPUT:
- `"status": "success"` + no `chain.next` → fast path to commit (skip Phase 2)
- `chain.next` includes tester → proceed to Phase 2

### Phase 2: REGRESSION TEST

```
Task(tester, "
  Run regression tests for fix:
  Context: fix={debugger_output}, files={debugger_artifacts}, root_cause={root_cause}
  Focus: regression test for fix area + affected components
")
```

### Phase 3: REVIEW + COMMIT

```
Task(reviewer, "
  Review bug fix:
  Context: fix={debugger_output}, tests={tester_output}
  Check: fix correctness, no regressions introduced, markers present
")
```

If review passes:

```
Task(git-ops, "
  Commit fix:
  Type: fix({scope}): {description}
  Files: {all_artifacts}
  Issue: {issue_reference}
")
```

## Fast path

If debugger's CHAIN_OUTPUT has:

```json
{ "status": "success", "chain": {"next": []} }
```

Skip directly to review+commit (debugger already created the regression test).

## Context flow

```
Pre-analysis → Debugger → Tester → Reviewer → Git-ops
     ↓            ↓          ↓          ↓
  hints       fix+RCA    test results  approval
```

## Examples

### Example 1: Standard cycle

```
$ /debug "TypeError: Cannot read property 'id' of undefined at user.controller.ts:42"
[Phase 0: PRE-ANALYZE] → likely cause: missing await on async DB call
[Phase 1: FIX]         → debugger: added await + null guard, regression test added
[Phase 2: REGRESSION]  → tester: 3/3 pass
[Phase 3: REVIEW]      → reviewer: APPROVED
[Phase 3: COMMIT]      → git-ops: fix(user): guard against undefined user in controller
```

### Example 2: Fast path

```
$ /debug "validation regex misses Unicode emails"
[Phase 0: PRE-ANALYZE] → suggest broaden character class
[Phase 1: FIX]         → debugger: fix + regression test in same step (CHAIN_OUTPUT.chain.next=[])
[Phase 3: REVIEW]      → APPROVED (Phase 2 skipped)
[Phase 3: COMMIT]      → fix(validation): support Unicode emails
```

## Output schema

```
=== /debug: <error> ===
Phase 0: pre-analysis (<duration>) → <likely cause>
Phase 1: fix (<duration>) → <files changed>
Phase 2: regression (<duration>) → <pass/fail>
Phase 3: review+commit → commit=<sha>
TOTAL: <duration>
```

## Related

- See `/coord` for thread coordination (auto-claimed)
- See `/track` for task registration (auto-called)
- See `/review` for standalone review without the debug cycle
- See `/implement` if the fix requires new functionality (chain into it)
