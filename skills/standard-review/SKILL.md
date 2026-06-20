---
name: standard-review
description: >
  Parent methodology framework for all code-review work — enforces a READ-ONLY
  reviewer, a pre-scan classification step, an explicit review status, and a
  conditional test-gap fill. Domain add-ons (security-review-addon, perf-review-addon)
  extend this standard with focus-specific checklists.
version: 1.0.0
type: standard-logic
addon_for: [reviewer]
extends: null
auto_activate:
  - pattern: ".*"   # always active when the reviewer agent runs
triggers: [review standard, code review, read-only review, owasp review, sop check, test gaps]
author: Claude Code
created: 2026-05-20
---

# Standard Review Methodology

> **Mandatory framework for the reviewer agent.**
> The reviewer is READ-ONLY — it never edits or commits. It reports findings + a status.
> Domain add-ons (e.g. `security-review-addon`) plug in at Phase 1 with focus checklists.

---

## Phase Overview

```
Phase 0: PRE-SCAN     — classify diff (focus + priority) at zero API cost
Phase 1: REVIEW       — quality + security + markers + SOP (READ-ONLY)
Phase 2: TEST-VERIFY  — fill coverage gaps (only if Phase 1 found gaps)
Phase 3: COMMIT       — commit test additions (conditional)
```

---

## Hard Gates

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 1 | Reviewer uses NO Write/Edit | Any mutation voids the review |
| Phase 1 | Explicit status emitted | Cannot proceed without a verdict |
| Phase 3 | `CHANGES_REQUESTED` is unresolved | Must NOT be merged |

## Branching Gates

| Condition | Action | Affected phase |
|---|---|---|
| Phase 1 found coverage gaps (`chain.next` includes tester) | Run test-verify | Phase 2 |
| No gaps found | Skip to verdict | Phase 2/3 skipped |
| Status `CHANGES_REQUESTED` | Hand back to author/implement loop | exit |

---

## Phase 0 — PRE-SCAN

**Rule: Classify before reading line-by-line.** Use the local LLM (no API cost) to set focus + priority.

```bash
# Determine: change type, risk surface, which checklists matter
git diff --stat
```

Output: `{ focus: [security|perf|quality], priority: high|med|low, files: [...] }`.

---

## Phase 1 — REVIEW (READ-ONLY)

**Rule: The reviewer agent must run with NO write access.** It reads, it reports — it does not fix.

```bash
Agent(subagent_type="reviewer", model="sonnet",
      prompt="Review the diff. Cover: code quality, OWASP Top-10, code markers (@MARK/@END-MARK/@MARK-RELATE), SOP compliance, naming, structure. READ-ONLY. Return a findings list + a status.")
```

Checklist (baseline — add-ons extend this):
- [ ] Correctness + edge cases
- [ ] OWASP Top-10 surface (injection, authz, secrets, SSRF…)
- [ ] Code markers present on new files >5 lines
- [ ] Naming + project-structure conventions
- [ ] Test coverage adequacy (flag gaps for Phase 2)

**Status (mandatory verdict)**: `APPROVED (no issues)` | `APPROVED (minor)` | `CHANGES_REQUESTED` | `FAILED`.

---

## Phase 2 — TEST-VERIFY (conditional)

**Rule: Only when Phase 1 flagged coverage gaps.** A tester (not the reviewer) writes the missing tests.

```bash
Agent(subagent_type="tester", model="sonnet",
      prompt="Fill the coverage gaps the reviewer flagged: <gaps>. Write + run tests.")
```

---

## Phase 3 — COMMIT (conditional)

**Rule: Only commits the test additions from Phase 2** (the reviewed code is committed by its own author/implement flow).

```bash
Agent(subagent_type="git-ops", model="haiku",
      prompt="Commit the added tests as `test(...)`; do not push unless told.")
```

Deliverable — final CHAIN_OUTPUT:

```json
{
  "status": "APPROVED | APPROVED (minor) | CHANGES_REQUESTED | FAILED",
  "findings": [{ "severity": "high|med|low", "file": "...", "note": "..." }],
  "coverage_gaps_filled": true,
  "artifacts": ["<test files added, if any>"]
}
```

---

## Gate Summary

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 1 | READ-ONLY (no Write/Edit) | Mutation voids review |
| Phase 1 | Explicit status verdict | Cannot proceed |
| Phase 3 | `CHANGES_REQUESTED` unresolved | Must not merge |

---

## Related agents / Domain add-ons

| Add-on | Covers | Invoke |
|---|---|---|
| *(future)* `security-review-addon` | OWASP deep-dive, secrets scan, authz matrix | `Skill(skill='security-review-addon')` |
| *(future)* `perf-review-addon` | N+1 queries, hot loops, allocation, bundle size | `Skill(skill='perf-review-addon')` |

> To add a domain add-on: create `skills/<name>/SKILL.md` with
> `type: standard-logic`, `extends: standard-review`, `addon_for: [reviewer]`.
