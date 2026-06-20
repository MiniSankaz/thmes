---
name: standard-security
description: >
  Parent methodology framework for all security-audit work — enforces OWASP-scoped
  scanning, true-positive validation with CVSS scoring, fix-then-verify for
  CRITICAL/HIGH findings, and full OWASP Top-10 coverage. Domain add-ons
  (owasp-web-addon, secrets-scan-addon) extend this standard with target specifics.
version: 1.0.0
type: standard-logic
addon_for: [reviewer]
extends: null
auto_activate:
  - pattern: ".*"   # always active during a security audit
triggers: [security standard, owasp, vulnerability, cvss, secrets scan, sast, audit only]
related_skills: [code-review-patterns]
author: Claude Code
created: 2026-05-20
---

# Standard Security Methodology

> **Mandatory framework for security-audit work** (hosted on the reviewer agent).
> Every finding is validated true-positive before action. CRITICAL/HIGH must be fixed + re-verified.
> OWASP Top-10 coverage is mandatory, not optional.
> Domain add-ons (e.g. `owasp-web-addon`) plug in at Phase 1–2 with target-specific checks.

---

## Phase Overview

```
Phase 0: SCOPE     — classify { scope, priority_owasp[], language }
Phase 1: SCAN      — npm audit + secret scan + SAST + config/infra
Phase 2: ANALYZE   — validate TP/FP + OWASP map + CVSS + blast radius (Hard Gate)
Phase 3: FIX       — fix CRITICAL/HIGH only (skippable in audit-only mode)
Phase 4: VERIFY    — re-scan + security tests + report (Hard Gate: crit/high closed)
```

---

## Hard Gates

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 2 | Every finding validated TP vs FP | Cannot prioritize/fix on noise |
| Phase 2 | All 10 OWASP categories considered | Incomplete audit |
| Phase 4 | All CRITICAL/HIGH fixed + re-verified (unless audit-only) | Cannot mark CLEAN/FIXED |

## Branching Gates

| Condition | Action | Affected phase |
|---|---|---|
| User said "audit only" / "report only" | Skip fixing | Phase 3 skipped |
| Dependency-only audit | Phase 1 = `npm audit` only → Phase 4 report | Phases 2–3 trimmed |
| No CRITICAL/HIGH found | Report CLEAN | Phase 3 skipped |

---

## Phase 0 — SCOPE

**Rule: Set scope + OWASP priority before scanning.**

Output: `{ "scope": "deps|code|infra|full", "priority_owasp": ["A01","A03",...], "language": "ts|py|..." }`.

---

## Phase 1 — SCAN

**Rule: Automated breadth first.**

```bash
Agent(subagent_type="ops", model="sonnet",
      prompt="Run: npm audit; secret scan (gitleaks-style); SAST; config/infra checks. Report findings with severity.")
```

Findings carry severity: `CRITICAL | HIGH | MEDIUM | LOW`.

---

## Phase 2 — ANALYZE (Hard Gate)

**Rule: No fix on unvalidated noise. Map every finding to OWASP + score it.**

```bash
Agent(subagent_type="reviewer", model="sonnet",
      prompt="For each finding: confirm true-positive vs false-positive, map to OWASP Top-10, assign CVSS, estimate blast radius, prioritize.")
```

### OWASP Top-10 coverage (all considered)

`A01` Broken Access Control · `A02` Cryptographic Failures · `A03` Injection · `A04` Insecure Design · `A05` Security Misconfiguration · `A06` Vulnerable Components · `A07` Auth Failures · `A08` Data Integrity Failures · `A09` Logging/Monitoring Failures · `A10` SSRF

---

## Phase 3 — FIX (skippable in audit-only)

**Rule: Fix only validated CRITICAL/HIGH. Defer MEDIUM/LOW to issues.**

```bash
Agent(subagent_type="backend-dev", model="sonnet",
      prompt="Fix validated CRITICAL/HIGH: <list>. Narrowest fix at the boundary; add code markers + a regression/security test per fix.")
```

---

## Phase 4 — VERIFY + REPORT (Hard Gate)

**Rule: Re-scan to confirm closure; never claim fixed without re-verification.**

```bash
Agent(subagent_type="tester", model="sonnet",
      prompt="Re-scan; run security tests; confirm no regression; confirm CRITICAL/HIGH closed.")
```

Deliverable — final CHAIN_OUTPUT:

```json
{
  "status": "CLEAN | FIXED | PARTIAL | CRITICAL_UNFIXABLE",
  "findings": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
  "owasp_covered": ["A01","A02","A03","A04","A05","A06","A07","A08","A09","A10"],
  "fixed": ["<finding -> fix>"],
  "deferred_issues": ["ISS-XXX: <medium/low>"]
}
```

---

## Gate Summary

| Gate | Requirement | Blocks |
|---|---|---|
| Phase 2 | TP/FP validated + OWASP-mapped + CVSS | Cannot prioritize |
| Phase 2 | All 10 OWASP categories considered | Incomplete audit |
| Phase 4 | CRITICAL/HIGH closed + re-verified | Cannot mark CLEAN/FIXED |

---

## Related agents / Domain add-ons

| Skill / add-on | Covers | Invoke |
|---|---|---|
| `code-review-patterns` (pattern-library) | OWASP patterns, secure-code checklists | `Skill(skill='code-review-patterns')` |
| *(future)* `owasp-web-addon` | Web-specific A01–A10 deep checks (CSRF, CORS, headers) | `Skill(skill='owasp-web-addon')` |
| *(future)* `secrets-scan-addon` | Entropy/regex secret detection, history scrub | `Skill(skill='secrets-scan-addon')` |

> To add a domain add-on: create `skills/<name>/SKILL.md` with
> `type: standard-logic`, `extends: standard-security`, `addon_for: [reviewer]`.
