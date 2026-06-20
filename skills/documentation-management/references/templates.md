# Documentation Templates Reference

This file contains ready-to-use templates for common documentation types: README, API endpoints, and Architecture Decision Records (ADRs). Copy and adapt as needed.

---

## README Template

```markdown
# Project Name

Brief description of the project — one or two sentences explaining what it does and why it exists.

## Features

- Feature 1: brief explanation
- Feature 2: brief explanation

## Quick Start

```bash
npm install
npm run dev
```

## Installation

```bash
# Prerequisites
node >= 18.0.0
npm >= 9.0.0

# Install dependencies
npm install

# Environment setup
cp .env.example .env
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `DATABASE_URL` | — | PostgreSQL connection string |

## Documentation

- [API Reference](./docs/api/index.md)
- [Architecture Overview](./docs/architecture.md)
- [Contributing Guide](./CONTRIBUTING.md)
- [Changelog](./CHANGELOG.md)

## Development

```bash
npm run dev        # Start dev server
npm run build      # Production build
npm test           # Run tests
npm run lint       # Lint code
```

## License

MIT — see [LICENSE](./LICENSE) for details.
```

---

## API Documentation Template

```markdown
# API Endpoint Name

## Overview

Brief description of what this endpoint does and when to use it.

## Endpoint

```
METHOD /api/v1/path
```

## Authentication

Requires `Authorization: Bearer <token>` header. Obtain tokens via `POST /api/auth/token`.

## Request

### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Resource UUID |

### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | number | `1` | Page number |
| `limit` | number | `20` | Items per page (max 100) |

### Headers
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `Authorization` | string | Yes | Bearer token |
| `Content-Type` | string | Yes | `application/json` |

### Body

```json
{
  "field": "value",
  "nested": {
    "key": "value"
  }
}
```

### Body Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field` | string | Yes | Description of field |
| `nested.key` | string | No | Description of nested key |

## Response

### Success (200 OK)

```json
{
  "data": {
    "id": "uuid",
    "created_at": "2026-01-17T00:00:00Z"
  },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

### Error Responses

| Code | Error | Description |
|------|-------|-------------|
| `400` | `VALIDATION_ERROR` | Request body failed validation |
| `401` | `UNAUTHORIZED` | Missing or invalid token |
| `403` | `FORBIDDEN` | Token lacks required scope |
| `404` | `NOT_FOUND` | Resource does not exist |
| `409` | `CONFLICT` | Resource already exists |
| `422` | `UNPROCESSABLE` | Business logic validation failed |
| `500` | `INTERNAL_ERROR` | Server error — contact support |

Error body format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [
      { "field": "email", "message": "Invalid format" }
    ]
  }
}
```

## Examples

### cURL

```bash
curl -X POST https://api.example.com/api/v1/path \
  -H "Authorization: Bearer eyJhbG..." \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### TypeScript (fetch)

```typescript
const response = await fetch('/api/v1/path', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ field: 'value' }),
});
const data = await response.json();
```

## Rate Limiting

- 100 requests / minute per IP
- 1000 requests / hour per authenticated user
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
```

---

## ADR (Architecture Decision Record) Template

```markdown
# ADR-NNN: Decision Title

**Date**: 2026-01-17
**Status**: Proposed | Accepted | Deprecated | Superseded by [ADR-NNN]
**Deciders**: [Names or team]

---

## Context

Describe the situation, constraints, and forces at play. What problem exists?
Include relevant technical context (existing architecture, team size, deadlines).

## Decision Drivers

- Driver 1: performance requirement
- Driver 2: team familiarity
- Driver 3: operational complexity

## Options Considered

### Option A: [Name]

Brief description.

Pros:
- Pro 1
- Pro 2

Cons:
- Con 1
- Con 2

### Option B: [Name]

Brief description.

Pros:
- Pro 1

Cons:
- Con 1

## Decision

**Chosen option: Option A**, because [primary reason].

[Explain why this option was selected over alternatives. Be specific.]

## Consequences

### Positive
- Consequence 1
- Consequence 2

### Negative
- Trade-off 1
- Trade-off 2

### Neutral
- Implementation note

## Implementation Notes

Steps required to implement this decision:
1. Step 1
2. Step 2

## References

- [Relevant RFC or issue](https://link)
- [Prior art or benchmark](https://link)
```

---

## CONTRIBUTING Template

```markdown
# Contributing Guide

## Development Setup

```bash
git clone https://github.com/org/repo
cd repo
npm install
cp .env.example .env
npm run dev
```

## Branching Strategy

- `main` — production-ready code
- `develop` — integration branch
- `feat/description` — feature branches
- `fix/description` — bug fix branches

## Pull Request Process

1. Branch from `develop`
2. Write tests for new behavior
3. Update documentation if needed
4. Ensure CI passes
5. Request review from at least one maintainer

## Commit Convention

Follow Conventional Commits:
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `chore:` — maintenance

## Code Style

Run `npm run lint` before committing. Auto-format with `npm run format`.
```

---

*templates.md v1.1.0*
