---
name: database-patterns
description: >
  This skill should be used when the user asks to "design a database schema", "write Prisma models",
  "add database relations", "write a query", "optimize database performance", or needs guidance
  on indexing, migrations, data modeling patterns, or connection management.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [database, prisma, schema, model, migration, sql, query, postgres, mysql, mongodb]
  keywords_th: [ฐานข้อมูล, สคีมา, โมเดล, ตาราง, ไมเกรชัน, คิวรี่, ดาต้าเบส]
---

# Database Patterns Skill

## Design Philosophy

```
Normalize to 3NF, denormalize for performance
Use appropriate data types
Index based on query patterns
Plan for scale from the start
```

---

## Prisma Schema Basics

### Model Structure
```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  password  String
  role      Role     @default(USER)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  posts     Post[]
  profile   Profile?

  @@index([email])
  @@map("users")
}

enum Role {
  USER
  ADMIN
}
```

---

## Relationships

### One-to-Many
```prisma
model User {
  id    String @id @default(cuid())
  posts Post[]
}

model Post {
  id     String @id @default(cuid())
  title  String
  userId String
  user   User   @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([userId])
}
```

### One-to-One
```prisma
model User {
  id      String   @id @default(cuid())
  profile Profile?
}

model Profile {
  id     String  @id @default(cuid())
  bio    String?
  userId String  @unique
  user   User    @relation(fields: [userId], references: [id], onDelete: Cascade)
}
```

### Many-to-Many
```prisma
model Post {
  id   String @id @default(cuid())
  tags Tag[]
}

model Tag {
  id    String @id @default(cuid())
  name  String @unique
  posts Post[]
}

// Explicit join table — use when extra fields needed
model PostTag {
  postId    String
  tagId     String
  createdAt DateTime @default(now())
  post Post @relation(fields: [postId], references: [id])
  tag  Tag  @relation(fields: [tagId], references: [id])
  @@id([postId, tagId])
}
```

### Self-Relation (Hierarchical)
```prisma
model Category {
  id       String     @id @default(cuid())
  name     String
  parentId String?
  parent   Category?  @relation("CategoryTree", fields: [parentId], references: [id])
  children Category[] @relation("CategoryTree")
}
```

---

## Indexing Strategy

```prisma
model User {
  id        String   @id
  email     String   @unique
  name      String
  status    String
  createdAt DateTime

  @@index([email])                  // single column
  @@index([status, createdAt])      // composite — order matters
  @@index([name], type: Gin)        // full-text (PostgreSQL)
}
```

### Index When
- Column used in WHERE clauses
- Column used in JOIN conditions
- Column used in ORDER BY
- Foreign key columns
- Unique constraints

### Skip Index When
- Small tables (< 1,000 rows)
- Columns with low cardinality (e.g., boolean flags)
- Frequently updated columns
- Tables with heavy write-to-read ratio

---

## Connection Management

Always use the singleton pattern — prevents connection pool exhaustion in serverless and hot-reload environments:

```typescript
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}
```

---

## Performance Rules

- Select only fields you need — avoid `findMany()` with no `select`
- Always paginate list queries with `take` + `skip` or cursor
- Use `createMany` / `updateMany` for batch operations
- Avoid N+1: use `include` instead of looping with `findMany`
- Use `$transaction` for operations that must be atomic

---

## Additional Resources

For detailed patterns, consult:
- **`references/prisma-patterns.md`** — Full CRUD, relations, filtering, pagination, aggregations, transactions, raw queries, migration commands
- **`references/modeling-patterns.md`** — Soft delete, audit trail, polymorphic relations, versioning/optimistic locking, multi-tenant, hierarchical data, performance DO/DON'T patterns

---

*Database Patterns Skill v1.2.0*
