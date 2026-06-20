# OpenAPI Specification Template

Complete OpenAPI 3.0 template with query parameter patterns, authentication, and schema components.

---

## Full OpenAPI Template

```yaml
openapi: 3.0.0
info:
  title: API Name
  version: 1.0.0
  description: |
    Brief description of the API.

    ## Authentication
    Use Bearer token in Authorization header.
  contact:
    name: API Support
    email: api@example.com

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

tags:
  - name: Users
    description: User management operations
  - name: Orders
    description: Order processing operations

paths:
  /users:
    get:
      summary: List users
      description: Returns a paginated list of users.
      tags: [Users]
      security:
        - BearerAuth: []
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
            minimum: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            minimum: 1
            maximum: 100
        - name: status
          in: query
          schema:
            type: string
            enum: [active, inactive, banned]
        - name: sort
          in: query
          description: "Field and direction: createdAt:desc"
          schema:
            type: string
            example: "createdAt:desc"
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserList'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'
    post:
      summary: Create user
      tags: [Users]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserInput'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '422':
          $ref: '#/components/responses/ValidationError'

  /users/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
    get:
      summary: Get user by ID
      tags: [Users]
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '404':
          $ref: '#/components/responses/NotFound'
    patch:
      summary: Update user
      tags: [Users]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateUserInput'
      responses:
        '200':
          description: Updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '422':
          $ref: '#/components/responses/ValidationError'
    delete:
      summary: Delete user
      tags: [Users]
      responses:
        '204':
          description: Deleted
        '404':
          $ref: '#/components/responses/NotFound'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          example: "cld_abc123"
        name:
          type: string
          example: "John Doe"
        email:
          type: string
          format: email
        role:
          type: string
          enum: [USER, ADMIN]
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
      required: [id, email, role, createdAt, updatedAt]

    CreateUserInput:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        email:
          type: string
          format: email
        password:
          type: string
          minLength: 8
      required: [name, email, password]

    UpdateUserInput:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        email:
          type: string
          format: email

    UserResponse:
      type: object
      properties:
        success:
          type: boolean
          example: true
        data:
          $ref: '#/components/schemas/User'
        meta:
          $ref: '#/components/schemas/Meta'

    UserList:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: array
          items:
            $ref: '#/components/schemas/User'
        pagination:
          $ref: '#/components/schemas/Pagination'

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        totalPages:
          type: integer
        hasNext:
          type: boolean
        hasPrev:
          type: boolean

    Meta:
      type: object
      properties:
        requestId:
          type: string

    Error:
      type: object
      properties:
        success:
          type: boolean
          example: false
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: array
              items:
                type: object
        meta:
          $ref: '#/components/schemas/Meta'

  responses:
    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    ValidationError:
      description: Validation failed
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    RateLimited:
      description: Too many requests
      headers:
        X-RateLimit-Limit:
          schema:
            type: integer
        X-RateLimit-Remaining:
          schema:
            type: integer
        X-RateLimit-Reset:
          schema:
            type: integer
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
```

---

## Query Parameter Patterns

### Filtering
```
GET /api/v1/users?status=active&role=admin
GET /api/v1/products?price[gte]=100&price[lte]=500
GET /api/v1/orders?createdAt[gte]=2026-01-01&createdAt[lte]=2026-01-31
```

### Sorting
```
GET /api/v1/users?sort=createdAt:desc
GET /api/v1/users?sort=-createdAt,name          # minus prefix = descending
GET /api/v1/users?sortBy=createdAt&sortDir=desc  # explicit fields
```

### Pagination
```
GET /api/v1/users?page=2&limit=20               # offset-based
GET /api/v1/users?cursor=abc123&limit=20        # cursor-based
```

### Field Selection
```
GET /api/v1/users?fields=id,name,email
GET /api/v1/users?select=id,name&expand=profile
```

### Search
```
GET /api/v1/users?q=john
GET /api/v1/users?search=john&searchFields=name,email
```

---

## Authentication Headers

### Bearer Token
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Key
```http
X-API-Key: ak_live_1234567890abcdef
```

### Rate Limit Response Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

---

*openapi-template.md v1.1.0*
