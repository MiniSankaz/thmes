# Security Review Reference

Security vulnerability patterns: credential exposure, SQL injection, XSS, input validation, authentication, and sensitive data handling.

---

## Credential Exposure

```typescript
// BAD — hardcoded secrets in code
const API_KEY = "sk-1234567890";
const DB_PASSWORD = "admin123";
const JWT_SECRET = "my-secret-key";

// GOOD — environment variables
const API_KEY = process.env.API_KEY;
if (!API_KEY) throw new Error('API_KEY env var required');

const DB_PASSWORD = process.env.DB_PASSWORD;
const JWT_SECRET = process.env.JWT_SECRET!;
```

**Scan commands:**
```bash
# Detect secrets in git history
git secrets --scan
git log --all -p | grep -E "(password|secret|api_key)\s*=\s*['\"][^'\"]{8,}"

# truffleHog scan
trufflehog git file://. --only-verified
```

**Patterns to flag:**
- String literals matching `sk-`, `pk-`, `ghp_`, `AKIA` (AWS key prefix)
- Variables named `password`, `secret`, `api_key` assigned string literals
- `.env` files committed to git

---

## SQL Injection

```typescript
// BAD — string concatenation
const query = `SELECT * FROM users WHERE id = ${userId}`;
const q2 = `SELECT * FROM posts WHERE title LIKE '%${search}%'`;

// GOOD — parameterized queries (pg)
const result = await db.query(
  'SELECT * FROM users WHERE id = $1',
  [userId]
);
const result2 = await db.query(
  'SELECT * FROM posts WHERE title ILIKE $1',
  [`%${search}%`]
);

// GOOD — Prisma (safe by default)
const user = await prisma.user.findUnique({
  where: { id: userId },
});

// GOOD — Knex
const users = await db('users').where('id', userId);

// BAD — raw query with interpolation
await prisma.$queryRaw(`SELECT * FROM users WHERE id = '${userId}'`);

// GOOD — raw query with template literal (auto-parameterized)
await prisma.$queryRaw`SELECT * FROM users WHERE id = ${userId}`;
```

---

## XSS Prevention

```typescript
// BAD — direct HTML insertion
element.innerHTML = userInput;
document.write(userInput);

// GOOD — text content (auto-escaped)
element.textContent = userInput;

// GOOD — sanitization when HTML is needed
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);

// React (safe by default — JSX auto-escapes)
return <div>{userInput}</div>;

// React DANGER — bypass (only use with sanitized input)
return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;

// CSP header
res.setHeader(
  'Content-Security-Policy',
  "default-src 'self'; script-src 'self'; object-src 'none'"
);
```

**Patterns to flag:**
- `innerHTML =` assigned from variable input
- `dangerouslySetInnerHTML` without prior sanitization
- Dynamic code execution via `new Function(userInput)` or `setTimeout(userInput, 0)`
- Missing CSP headers on HTML responses

---

## Input Validation

```typescript
// BAD — no validation, trusting client data
function updateUser(data: any) {
  return db.update('users', data);
}

// GOOD — schema validation with Zod
import { z } from 'zod';

const UpdateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
  age: z.number().int().min(0).max(150).optional(),
  role: z.enum(['USER', 'ADMIN']).optional(),
});

function updateUser(data: unknown) {
  const validated = UpdateUserSchema.parse(data);  // throws on invalid
  return db.update('users', validated);
}

// GOOD — validate file uploads
const FileUploadSchema = z.object({
  mimetype: z.enum(['image/jpeg', 'image/png', 'image/webp']),
  size: z.number().max(5 * 1024 * 1024), // 5MB max
});

// GOOD — sanitize string inputs
import { escape } from 'html-entities';
const safeHtml = escape(userInput);
```

---

## Authentication & Authorization

```typescript
// BAD — no auth check
router.delete('/users/:id', async (req, res) => {
  await userService.delete(req.params.id);
  res.status(204).send();
});

// GOOD — auth + authorization check
router.delete('/users/:id', requireAuth, async (req, res) => {
  // Check ownership or admin role
  if (req.user.id !== req.params.id && req.user.role !== 'ADMIN') {
    return res.status(403).json({
      error: { code: 'FORBIDDEN', message: 'Not authorized' }
    });
  }
  await userService.delete(req.params.id);
  res.status(204).send();
});

// BAD — predictable sequential IDs (enumeration attack)
router.get('/invoices/:id', async (req, res) => {
  const invoice = await Invoice.findById(req.params.id);
  res.json(invoice); // leaks other users' data
});

// GOOD — always scope queries to authenticated user
router.get('/invoices/:id', requireAuth, async (req, res) => {
  const invoice = await Invoice.findOne({
    where: { id: req.params.id, userId: req.user.id }, // ownership check
  });
  if (!invoice) return res.status(404).json({ error: 'Not found' });
  res.json(invoice);
});
```

---

## Sensitive Data in Logs

```typescript
// BAD — logging sensitive data
console.log('User login:', { email, password });
logger.info('Payment processed', { cardNumber, cvv });

// GOOD — log only non-sensitive fields
logger.info('User login attempt', { email, userId });
logger.info('Payment processed', { userId, last4: cardNumber.slice(-4) });

// GOOD — redaction helper
function redact(obj: Record<string, unknown>, keys: string[]) {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) =>
      keys.includes(k) ? [k, '[REDACTED]'] : [k, v]
    )
  );
}

const safeLog = redact(requestBody, ['password', 'token', 'cardNumber']);
logger.info('Request body', safeLog);
```

---

## CSRF Protection

```typescript
// Express with csurf
import csrf from 'csurf';

const csrfProtection = csrf({ cookie: true });

router.get('/form', csrfProtection, (req, res) => {
  res.render('form', { csrfToken: req.csrfToken() });
});

router.post('/submit', csrfProtection, (req, res) => {
  // CSRF token validated automatically
});

// SameSite cookie (modern approach — no extra middleware needed)
res.cookie('session', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
});
```

---

## Path Traversal

```typescript
// BAD — direct path from user input
const filePath = `./uploads/${req.params.filename}`;
const content = fs.readFileSync(filePath);

// GOOD — resolve and validate path stays within allowed directory
import path from 'path';

const UPLOAD_DIR = path.resolve('./uploads');
const requestedPath = path.resolve(UPLOAD_DIR, req.params.filename);

if (!requestedPath.startsWith(UPLOAD_DIR + path.sep)) {
  return res.status(400).json({ error: 'Invalid file path' });
}

const content = fs.readFileSync(requestedPath);
```

---

*security-review.md v1.1.0*
