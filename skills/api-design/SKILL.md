---
name: api-design
description: >
  This skill should be used when the user asks to "design an API", "create REST endpoints",
  "define API contracts", "set up HTTP routes", "design response format", or needs guidance
  on RESTful conventions, HTTP methods, status codes, versioning, or OpenAPI specifications.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [api, endpoint, rest, http, route, controller, swagger, openapi, graphql]
  keywords_th: [เอพีไอ, เส้นทาง, เซอร์วิส, เร้าท์, คอนโทรลเลอร์, เอนด์พอยต์]
---

# API Design Skill

## RESTful Design Principles

```
Use nouns for resources, not verbs
Use HTTP methods for actions
Use plural resource names
Use consistent naming conventions
```

---

## HTTP Methods

| Method | Usage | Example |
|--------|-------|---------|
| **GET** | Retrieve resource(s) | `GET /users`, `GET /users/123` |
| **POST** | Create new resource | `POST /users` |
| **PUT** | Replace entire resource | `PUT /users/123` |
| **PATCH** | Update partial resource | `PATCH /users/123` |
| **DELETE** | Remove resource | `DELETE /users/123` |

---

## URL Structure

### Good
```
GET    /api/v1/users              # List users
GET    /api/v1/users/123          # Get user by ID
POST   /api/v1/users              # Create user
PATCH  /api/v1/users/123          # Update user
DELETE /api/v1/users/123          # Delete user

GET    /api/v1/users/123/orders   # Get user's orders
POST   /api/v1/users/123/orders   # Create order for user
```

### Bad
```
GET    /api/getUsers              # Verb in URL
GET    /api/user/list             # Inconsistent naming
POST   /api/createUser            # Verb in URL
GET    /api/v1/user               # Singular (should be plural)
```

---

## HTTP Status Codes

### Success (2xx)
| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |

### Client Errors (4xx)
| Code | Meaning | Use Case |
|------|---------|----------|
| 400 | Bad Request | Invalid input/format |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |

### Server Errors (5xx)
| Code | Meaning | Use Case |
|------|---------|----------|
| 500 | Internal Server Error | Unexpected errors |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service down/maintenance |

---

## Response Format

### Success
```json
{
  "success": true,
  "data": { "id": "123", "name": "John Doe", "email": "john@example.com" },
  "meta": { "requestId": "req-abc123" }
}
```

### List with Pagination
```json
{
  "success": true,
  "data": [{ "id": "1" }, { "id": "2" }],
  "pagination": {
    "page": 1, "limit": 20, "total": 150,
    "totalPages": 8, "hasNext": true, "hasPrev": false
  }
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [{ "field": "email", "message": "Must be a valid email address" }]
  },
  "meta": { "requestId": "req-abc123" }
}
```

---

## API Versioning

### URL Versioning (Recommended)
```
/api/v1/users
/api/v2/users
```

### Header Versioning
```
GET /api/users
Accept: application/vnd.api+json;version=1
```

**Rules:**
- Increment MAJOR version for breaking changes (removed fields, changed types, new required params)
- Keep v1 alive for at least 6 months after v2 launch
- Return `Deprecation` header on old versions: `Deprecation: version="v1", sunset="2026-12-31"`

---

## Authentication Headers

```
Authorization: Bearer <token>     # JWT / OAuth2
X-API-Key: <api-key>              # API key auth
```

### Rate Limiting Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

---

## Additional Resources

For detailed patterns, consult:
- **`references/endpoint-examples.md`** — TypeScript/Express CRUD implementation, error handler, auth middleware, rate limiter
- **`references/openapi-template.md`** — Full OpenAPI 3.0 spec template, query parameter patterns, schema components

---

*API Design Skill v1.2.0*
