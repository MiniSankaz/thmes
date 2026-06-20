---
name: standard-test
description: >
  Parent methodology framework for all testing work — enforces scope-before-write,
  a coverage gate (≥80% lines / ≥75% branches, ≥90% critical paths), the 3-layer SPA verification
  rule, and bounded anti-loop E2E. Pulls pattern detail from the testing-patterns
  library; domain add-ons (unit-test-addon, e2e-addon) extend with stack specifics.
version: 1.0.0
type: standard-logic
addon_for: [tester]
extends: null
auto_activate:
  - pattern: ".*"   # always active when the tester agent runs
triggers: [test standard, coverage gate, write tests, e2e, playwright, spa verification, anti-loop]
related_skills: [testing-patterns]
author: Claude Code
created: 2026-05-20
---

# Standard Test Methodology

> **Mandatory framework for the tester agent.**
> Phases define the *workflow*; `testing-patterns` (pattern-library) holds the *how-to* catalog —
> this framework references it, never duplicates it.
> Domain add-ons (e.g. `e2e-addon`) plug in at Phase 1–2 with stack-specific templates.

---

## Phase Overview

```
Phase 0: SCOPE     — what to test + which type (unit/integration/E2E) + risk areas
Phase 1: WRITE     — Arrange-Act-Assert; one concept/test; test behavior not impl
Phase 2: RUN       — execute; tests must fail for the RIGHT reasons
Phase 3: COVERAGE  — Hard Gate: ≥80% lines / ≥75% branches (≥90% critical)
Phase 4: REPORT    — pass/fail + coverage + gaps + (SPA) 3-layer verification
```

---

## Hard Gates

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 2 | Tests fail for the right reason (not flaky/false-green) | Cannot trust coverage |
| Phase 3 | Coverage ≥80% lines / ≥75% branches; ≥90% on critical paths (auth, payment, validation) | Cannot report PASS |
| Phase 4 (SPA/PWA) | L1 (HTTP 200) + L2 (JS import resolves) + L3 (real-browser click) all pass | Cannot claim UI works |

## Branching Gates

| Condition | Action | Affected phase |
|---|---|---|
| Backend/logic only (no UI) | Skip L3 browser layer | Phase 4 |
| UI / SPA / PWA change | Mandatory 3-layer verification + bump SW version on build-hash change | Phase 4 |
| Long-running external dep | Use bounded waits — never sleep-loops (anti-loop rule) | Phase 2 |

---

## Phase 0 — SCOPE

**Rule: Decide what + which level before writing.**

| Level | Use for | Tool |
|---|---|---|
| Unit | pure functions, branches, edge cases | Vitest/Jest |
| Integration | module + DB/API boundaries | Vitest + test DB |
| E2E | user-visible flows | Playwright |

Output: list of cases (normal + boundary + the risky path).

---

## Phase 1 — WRITE

**Rule: Test behavior, not implementation. One concept per test. Arrange-Act-Assert.** See `testing-patterns` for templates/mocking/MSW.

```bash
Skill(skill='testing-patterns')   # pull file structure, mocking, Playwright templates
```

---

## Phase 2 — RUN

**Rule: A test that can't fail is worthless — confirm it fails for the right reason.**

```bash
npm test                 # unit + integration
npx playwright test      # E2E (bounded, no sleep loops)
```

---

## Phase 3 — COVERAGE (Hard Gate)

**Rule: Below the bar = not done.**

```bash
npm test -- --coverage
# Bar: ≥80% lines / ≥75% branches; ≥90% on auth / payment / validation / money paths
```

Deliverable before Phase 4:
- [ ] Coverage ≥80% lines / ≥75% branches (≥90% critical)
- [ ] No flaky/false-green tests

---

## Phase 4 — REPORT (+ SPA 3-layer gate)

**Rule: "curl 200" is NOT enough for SPA/PWA.** Verify all three layers before claiming a UI works.

```bash
# L1 — HTTP reachable
curl -sI <url> | head -1
# L2 — JS import graph resolves (build/typecheck, no 404 chunks)
npm run build
# L3 — real browser click (Playwright) — the actual user action succeeds
npx playwright test e2e/<flow>.spec.ts
```

If build hashes changed, **bump the service-worker version** and tell users to hard-reload / unregister.

Deliverable — final CHAIN_OUTPUT:

```json
{
  "status": "PASS | FAIL",
  "tests": { "passed": 0, "failed": 0 },
  "coverage": { "lines": "X%", "critical": "Y%" },
  "spa_verification": "L1+L2+L3 PASS | n/a (no UI)",
  "gaps": ["<uncovered area, if any>"]
}
```

---

## Gate Summary

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 2 | Tests fail for right reasons | Coverage untrustworthy |
| Phase 3 | ≥80% lines / ≥75% branches; ≥90% critical | Cannot report PASS |
| Phase 4 | SPA L1+L2+L3 (UI changes) | Cannot claim UI works |

---

## Related agents / Domain add-ons

| Skill / add-on | Covers | Invoke |
|---|---|---|
| `testing-patterns` (pattern-library) | Test structure, mocking, MSW, Playwright templates, anti-loop rules | `Skill(skill='testing-patterns')` |
| *(future)* `unit-test-addon` | Branch/edge generators, property-based testing | `Skill(skill='unit-test-addon')` |
| *(future)* `e2e-addon` | Playwright fixtures, network stubbing, visual diff | `Skill(skill='e2e-addon')` |

> To add a domain add-on: create `skills/<name>/SKILL.md` with
> `type: standard-logic`, `extends: standard-test`, `addon_for: [tester]`.
