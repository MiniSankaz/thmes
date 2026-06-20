# Review Comment Templates

Structured templates for code review comments, severity classifications, and PR feedback patterns.

---

## Severity Levels

| Level | Description | Action Required | Merge? |
|-------|-------------|-----------------|--------|
| **Blocker** | Security vulnerability, data loss risk, auth bypass | Must fix before merge | No |
| **Critical** | Significant bug, breaking change, broken tests | Must fix before merge | No |
| **Major** | Performance issue, poor design, missing error handling | Should fix — discuss timeline | Conditional |
| **Minor** | Code style, inconsistent naming, dead code | Nice to fix — non-blocking | Yes |
| **Suggestion** | Alternative approach, optimization idea | Optional — for discussion | Yes |
| **Praise** | Good pattern, clever solution, helpful abstraction | None needed | Yes |

---

## Comment Templates

### Blocker — Security

```
[BLOCKER] Security: {issue title}

**Problem**: {Describe the vulnerability and what an attacker can do}
**Impact**: {Data exposure / account takeover / etc.}
**Fix**:

```{language}
// BAD
{current code}

// GOOD
{fixed code}
```

References: {OWASP link or standard}
```

### Critical — Bug

```
[CRITICAL] Bug: {issue title}

**Problem**: {What goes wrong and when}
**Repro**: {Steps to reproduce or test case}
**Fix**: {Suggested fix}

```{language}
{fixed code}
```
```

### Major — Performance

```
[MAJOR] Performance: {issue title}

**Problem**: {N+1 query / memory leak / blocking call / etc.}
**Impact**: {Response time / memory / throughput impact}
**Fix**:

```{language}
// Before: {N queries for N users}
{current code}

// After: {1 query}
{fixed code}
```
```

### Major — Missing Error Handling

```
[MAJOR] Missing error handling: {function/operation}

**Problem**: If {condition}, this throws an unhandled exception.
**Impact**: {500 response to user / data loss / silent failure}
**Fix**:

```{language}
{code with proper error handling}
```
```

### Minor — Naming

```
[MINOR] Naming: `{variable}` could be more descriptive

**Suggestion**: Rename to `{betterName}` to clarify {what it represents}.

This is non-blocking — apply at your discretion.
```

### Suggestion — Alternative Approach

```
[SUGGESTION] Alternative: {brief title}

Not a blocker, but worth considering:

```{language}
{alternative code}
```

**Why**: {Reason — simpler / more performant / idiomatic / etc.}
```

### Asking for Clarification

```
[QUESTION] {Topic}

**Context**: I'm not sure I understand {what this code does / why this approach was chosen}.
**Question**: {Specific question}

Could you add a comment explaining this, or clarify in a reply?
```

### Praise

```
[NICE] Great pattern here — {brief description}

{Why it's good — readable / clever / good use of abstraction}
```

---

## PR Review Summary Template

```markdown
## Review Summary

**Overall**: {Approved / Needs Changes / Requesting Discussion}

### Blockers (must fix before merge)
- Line 45: SQL injection via string concatenation
- Line 78: No auth check on DELETE endpoint

### Should Fix
- Line 23: N+1 query — use `include` instead of loop
- Line 156: Missing error handling in payment flow

### Minor / Suggestions
- Line 12: `data` could be renamed `userData` for clarity
- Lines 34-40: Could simplify with array `.reduce()`

### Positive Notes
- Good test coverage on the happy path
- Error responses follow the standard format consistently
```

---

## Quick Checklist Reference

### Security
```
- [ ] No hardcoded credentials/secrets
- [ ] No SQL injection (parameterized queries)
- [ ] No XSS (textContent or sanitization)
- [ ] Input validated with schema
- [ ] Auth checks on all mutating endpoints
- [ ] No sensitive data in logs
- [ ] CSRF protection on state-changing endpoints
- [ ] No path traversal in file operations
```

### Code Quality
```
- [ ] Functions do one thing (SRP)
- [ ] Descriptive names (no x, y, data, tmp)
- [ ] No code duplication (DRY)
- [ ] Proper error handling (specific, not generic catch-all)
- [ ] No dead code or TODO comments in production
- [ ] Magic numbers extracted to named constants
```

### Performance
```
- [ ] No N+1 queries
- [ ] Pagination on list endpoints
- [ ] Select only needed fields
- [ ] No unbounded loops over DB results
- [ ] No memory leaks (event listeners cleaned up)
- [ ] Async operations not blocking event loop
```

### Testing
```
- [ ] Tests included for new functionality
- [ ] Edge cases covered (null, empty, max values)
- [ ] Error conditions tested
- [ ] Tests are independent (no shared state)
- [ ] No test only passes in specific order
```

---

## Review Commands

```bash
# View full diff for review
git diff main...feature-branch

# Changed files only
git diff --name-only main...feature-branch

# Specific file history
git log --follow -p src/services/user.service.ts

# Check for accidentally committed secrets
git secrets --scan
git log --all -p | grep -i "password\s*="

# Run full validation suite
npm run lint && npm run typecheck && npm test
```

---

*review-templates.md v1.1.0*
