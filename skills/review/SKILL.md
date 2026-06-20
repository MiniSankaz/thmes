---
name: review
description: >
  This skill should be used when the user asks to "review code changes", "audit a diff",
  "check a pull request", "inspect recent commits", or needs a structured 3-phase code
  review cycle (pre-scan → review → test gaps → commit) with automated pre-scan.
version: 1.2.1
type: workflow
triggers:
  keywords_en: [review, audit, code review, diff review, pull request, inspect commits]
  keywords_th: [ตรวจสอบ, รีวิว, ตรวจโค้ด, ออดิท]
verbs:
  - name: run
    purpose: Execute the 3-phase review cycle (pre-scan → review → test gaps → commit)
    inputs: [scope]
    outputs: text+report
required_tools: [Read, Grep, Bash]
related_skills:
  - coord: claim a coord thread for the review
  - track: register the review as a task
  - debug: chain into /debug if reviewer flags critical bugs
  - testing-patterns: knowledge skill for fill-the-gaps tests
  - standard-review: parent methodology framework this skill applies (read-only review + gates)
related_agents:
  - reviewer: Phase 1 review (sonnet, READ-ONLY)
  - tester: Phase 2 fill coverage gaps (sonnet)
  - git-ops: Phase 3 commit (haiku)
---

# /review — Code Review Cycle

> Workflow skill that drives a structured review through 3 phases. Phase 0 uses local LLM
> for scope classification; Phase 1 delegates to read-only `reviewer`; Phase 2 calls
> `tester` to fill coverage gaps; Phase 3 commits any tester additions.

## When to invoke

- Need a thorough pre-merge review of a PR or diff
- Want a security/quality audit of recent commits
- Refactoring is complete and needs a final-pass check
- Test coverage feels thin and need to formalise gap-filling

## When NOT to invoke

- A specific bug needs investigation → use `/debug`
- Want full feature workflow → use `/implement` (review is Phase 5 there)
- Just want to read patterns documentation → call `code-review-patterns` knowledge skill
- Architecture review (no code yet) → call `architect` agent directly

## Verbs (detailed)

### `/review [scope]` — run the cycle

**Input**: `[scope]` — optional file paths, commit ranges, or `HEAD~5..HEAD`. If omitted, reviews the working diff.
**Output**: text — review report + commit info.
**Side effects**:
- Creates coord thread covering the cycle
- Spawns reviewer (READ-ONLY — no edits)
- May spawn tester to add coverage
- May commit tester additions

## Methodology

This skill orchestrates the **`standard-review`** parent framework — a READ-ONLY reviewer, pre-scan classification, an explicit review status, and conditional test-gap fill. For the full methodology + gates, invoke `Skill(skill='standard-review')`.

---

## Phase workflow

### Phase 0: PRE-SCAN (local LLM — zero API cost)

```bash
SCOPE=$(llm-query --classify "Review scope: {changes_description}" --model fast)
```

Use classification to determine review focus and priority.

### Phase 1: REVIEW

```
Task(reviewer, "
  Comprehensive code review:
  Scope: {files_or_changes}
  Pre-scan priority: {local_llm_classification}

  Check all:
  - Code quality (TypeScript strict, no any, error handling)
  - Security (OWASP Top 10)
  - Marker compliance (100% @MARK coverage)
  - SOP compliance (commits, imports, file size)
  - Project structure (naming, boundaries)
  - Test coverage adequacy
")
```

> reviewer is READ-ONLY (`disallowedTools: Write, Edit`). Findings are returned as text.

### Phase 2: TEST VERIFY (only if reviewer found coverage gaps)

Parse reviewer's CHAIN_OUTPUT — if `chain.next` includes tester:

```
Task(tester, "
  Fill test coverage gaps found during review:
  Context: review_findings={reviewer_output}, coverage_gaps={reviewer_issues}
  Create tests for: {uncovered_areas}
")
```

### Phase 3: COMMIT (if review passes or after tester additions)

```
Task(git-ops, "
  Commit test additions (if any):
  Type: test({scope}): add coverage for {areas}
  Files: {tester_artifacts}
")
```

## Orchestrator actions

The orchestrator (this skill's caller) may apply reviewer suggestions directly via Edit
for unambiguous fixes — typos, missing imports, formatting. Keep this narrow; route
substantive changes back through `/debug` or `/implement`.

## Review result handling

| Review Status | Action |
|---|---|
| APPROVED (no issues) | Skip to commit or report success |
| APPROVED (minor only) | Report findings, no blocking |
| CHANGES_REQUESTED | Route critical issues to appropriate dev agent (chain into `/debug` or `/implement`) |
| FAILED | Escalate to user |

## Examples

### Example 1: Standard PR review

```
$ /review HEAD~3..HEAD
[Phase 0: PRE-SCAN] → scope=backend-feature priority=normal
[Phase 1: REVIEW]   → reviewer: APPROVED (2 minor: missing @MARK in src/auth/jwt.ts)
[Phase 2: TEST]     → SKIPPED (no coverage gaps)
DONE: report posted, no commits added
```

### Example 2: Coverage-gap fill

```
$ /review src/payment/
[Phase 1: REVIEW]   → reviewer: CHANGES_REQUESTED (no tests for refundService.ts)
[Phase 2: TEST]     → tester: added 8 unit tests, all pass
[Phase 3: COMMIT]   → git-ops: test(payment): add coverage for refundService
```

## Output schema

```
=== /review: <scope> ===
Phase 0: scope=<class> priority=<level>
Phase 1: <APPROVED|CHANGES_REQUESTED|FAILED> findings=<N>
Phase 2: <SKIPPED|added <N> tests>
Phase 3: <SKIPPED|commit=<sha>>
TOTAL: <duration>
```

## Related

- See `/coord` for the coord thread (auto-claimed)
- See `/track` for task registration
- See `/debug` to follow up on bugs reviewer found
- See `/implement` if review surfaces missing functionality (chain into it)
- See `code-review-patterns` knowledge skill for review checklists / OWASP patterns
