---
name: code-review-patterns
description: >
  This skill should be used when the user asks to "review code", "audit for security",
  "check code quality", "review a pull request", "inspect for vulnerabilities", or needs
  guidance on review checklists, security patterns, or code quality best practices.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [review, audit, quality, inspect, check code, pull request, pr, merge request]
  keywords_th: [รีวิว, ตรวจสอบ, คุณภาพ, ตรวจโค้ด, ตรวจสอบโค้ด, พีอาร์]
---

# Code Review Patterns Skill

## Review Philosophy

```
Review the code, not the person
Provide constructive feedback with examples
Focus on important issues first
Be specific and actionable
```

---

## Quick Review Checklist

### Security (Critical)
- [ ] No hardcoded credentials/secrets
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Proper input validation
- [ ] Proper authentication checks on all mutating endpoints
- [ ] No sensitive data in logs

### Code Quality
- [ ] Clear, descriptive naming
- [ ] Functions do one thing (SRP)
- [ ] No unnecessary complexity
- [ ] Proper error handling
- [ ] No code duplication (DRY)

### Performance
- [ ] No N+1 queries
- [ ] Proper indexing suggested
- [ ] No memory leaks
- [ ] Async operations handled correctly

### Testing
- [ ] Tests included for new code
- [ ] Tests cover edge cases
- [ ] Tests are meaningful (not just coverage numbers)

---

## Code Quality Patterns

### Naming
```typescript
// BAD
const x = getData();
function fn(a, b) { }
const arr = users.filter(u => u.a);

// GOOD
const activeUsers = fetchActiveUsers();
function calculateDiscount(price: number, percentage: number) { }
const adminUsers = users.filter(user => user.isAdmin);
```

### Single Responsibility
```typescript
// BAD — one function doing too many things
function processUser(user) {
  validateUser(user);
  saveToDatabase(user);
  sendEmail(user);
  updateAnalytics(user);
  return formatResponse(user);
}

// GOOD — orchestrate, don't inline
async function processUser(user) {
  const validated = validateUser(user);
  const saved = await saveUser(validated);
  await Promise.all([
    notificationService.sendWelcomeEmail(saved),
    analyticsService.trackUserCreated(saved),
  ]);
  return formatUserResponse(saved);
}
```

### Error Handling
```typescript
// BAD — generic catch-all
try {
  await doSomething();
} catch (e) {
  throw new Error('Something went wrong');
}

// GOOD — specific, contextual handling
try {
  await doSomething();
} catch (error) {
  if (error instanceof ValidationError) {
    throw new BadRequestError(error.message);
  }
  if (error instanceof NotFoundError) {
    throw new NotFoundError(`Resource not found: ${error.resourceId}`);
  }
  logger.error('Unexpected error in doSomething', { error });
  throw new InternalError('Failed to process request');
}
```

---

## Performance Review

### Database — N+1 Queries
```typescript
// BAD — N+1
const users = await User.findAll();
for (const user of users) {
  const orders = await Order.findByUserId(user.id); // N queries
}

// GOOD — eager loading
const users = await User.findAll({
  include: [{ model: Order }],
});
```

### Memory — Unbounded Cache
```typescript
// BAD — grows forever
const cache = {};
function addToCache(key, value) {
  cache[key] = value;
}

// GOOD — bounded LRU
import LRU from 'lru-cache';
const cache = new LRU({ max: 500 });
function addToCache(key, value) {
  cache.set(key, value);
}
```

---

## Severity Reference

| Level | Description | Merge? |
|-------|-------------|--------|
| **Blocker** | Security vulnerability, data loss risk | No |
| **Critical** | Significant bug, breaking change | No |
| **Major** | Performance issue, poor patterns | Conditional |
| **Minor** | Style, naming | Yes |
| **Suggestion** | Alternative approach | Yes |

---

## Quick Commands

```bash
# View diff
git diff main...feature-branch

# View changed files only
git diff --name-only main...feature-branch

# Check for secrets
git secrets --scan

# Full validation
npm run lint && npm run typecheck && npm test
```

---

## Additional Resources

For detailed patterns, consult:
- **`references/security-review.md`** — Credential exposure, SQL injection, XSS, input validation, auth/authorization, sensitive data in logs, CSRF, path traversal — each with BAD/GOOD code examples
- **`references/review-templates.md`** — Structured comment templates (Blocker/Critical/Major/Minor/Suggestion), PR summary template, full security/quality/performance/testing checklists

---

*Code Review Patterns Skill v1.2.0*
