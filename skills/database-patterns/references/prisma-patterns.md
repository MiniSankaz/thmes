# Prisma Client Patterns

Prisma client usage patterns: CRUD, relations, filtering, pagination, aggregations, transactions, and connection management.

---

## Basic CRUD

```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Create
const user = await prisma.user.create({
  data: {
    email: 'user@example.com',
    name: 'John',
  },
});

// Read single
const user = await prisma.user.findUnique({
  where: { id: 'user-id' },
});

// Read many
const users = await prisma.user.findMany({
  where: { role: 'ADMIN' },
  orderBy: { createdAt: 'desc' },
  take: 10,
});

// Update
const user = await prisma.user.update({
  where: { id: 'user-id' },
  data: { name: 'Jane' },
});

// Upsert
const user = await prisma.user.upsert({
  where: { email: 'user@example.com' },
  update: { name: 'Jane' },
  create: { email: 'user@example.com', name: 'Jane', password: 'hashed' },
});

// Delete
await prisma.user.delete({
  where: { id: 'user-id' },
});

// Delete many
await prisma.user.deleteMany({
  where: { status: 'BANNED' },
});
```

---

## Relations

```typescript
// Include relations
const userWithPosts = await prisma.user.findUnique({
  where: { id: 'user-id' },
  include: {
    posts: true,
    profile: true,
  },
});

// Select specific fields
const userPreview = await prisma.user.findUnique({
  where: { id: 'user-id' },
  select: {
    id: true,
    name: true,
    posts: {
      select: { title: true, createdAt: true },
      take: 5,
      orderBy: { createdAt: 'desc' },
    },
  },
});

// Nested create
const user = await prisma.user.create({
  data: {
    email: 'user@example.com',
    profile: {
      create: { bio: 'Hello!' },
    },
    posts: {
      create: [
        { title: 'Post 1' },
        { title: 'Post 2' },
      ],
    },
  },
  include: { profile: true, posts: true },
});

// Connect existing records
const post = await prisma.post.create({
  data: {
    title: 'New Post',
    author: { connect: { id: 'user-id' } },
    tags: { connect: [{ id: 'tag-1' }, { id: 'tag-2' }] },
  },
});

// Disconnect relation
await prisma.post.update({
  where: { id: 'post-id' },
  data: {
    tags: { disconnect: [{ id: 'tag-1' }] },
  },
});
```

---

## Filtering

```typescript
// Complex filters
const users = await prisma.user.findMany({
  where: {
    AND: [
      { email: { endsWith: '@company.com' } },
      { role: 'USER' },
    ],
    OR: [
      { name: { contains: 'john', mode: 'insensitive' } },
      { posts: { some: { published: true } } },
    ],
    NOT: { status: 'BANNED' },
  },
});

// Comparison operators
const users = await prisma.user.findMany({
  where: {
    age: { gte: 18, lt: 65 },
    email: { not: null },
    name: { in: ['John', 'Jane'] },
    createdAt: { gt: new Date('2026-01-01') },
  },
});

// Relation filters
const usersWithPublishedPosts = await prisma.user.findMany({
  where: {
    posts: {
      some: { published: true },   // at least one
      // every: { published: true },  // all
      // none: { published: true },   // none
    },
  },
});

// Full-text search (PostgreSQL)
const users = await prisma.user.findMany({
  where: {
    name: { search: 'john doe' },
  },
});
```

---

## Pagination

```typescript
// Offset pagination
const page = 2;
const limit = 10;
const users = await prisma.user.findMany({
  skip: (page - 1) * limit,
  take: limit,
  orderBy: { createdAt: 'desc' },
});

const total = await prisma.user.count({ where: {} });
const totalPages = Math.ceil(total / limit);

// Cursor pagination (better performance for large datasets)
const users = await prisma.user.findMany({
  take: 10,
  cursor: { id: 'last-seen-id' },
  skip: 1,  // skip the cursor itself
  orderBy: { id: 'asc' },
});
```

---

## Aggregations

```typescript
// Count
const count = await prisma.user.count({
  where: { role: 'USER' },
});

// Aggregate
const stats = await prisma.order.aggregate({
  _sum: { amount: true },
  _avg: { amount: true },
  _max: { amount: true },
  _min: { amount: true },
  _count: true,
  where: { status: 'COMPLETED' },
});

// Group by
const usersByRole = await prisma.user.groupBy({
  by: ['role'],
  _count: { id: true },
  _max: { createdAt: true },
  orderBy: { _count: { id: 'desc' } },
});
```

---

## Transactions

```typescript
// Sequential (array) — atomic, no interdependency
const [user, post] = await prisma.$transaction([
  prisma.user.create({ data: { email: 'a@b.com', password: 'hashed' } }),
  prisma.post.create({ data: { title: 'Hello', userId: 'existing-id' } }),
]);

// Interactive transaction — use when operations depend on each other
const result = await prisma.$transaction(async (tx) => {
  const user = await tx.user.create({ data: { email: 'a@b.com', password: 'hashed' } });

  const post = await tx.post.create({
    data: { title: 'Hello', userId: user.id },
  });

  // Debit/credit pattern
  await tx.account.update({
    where: { id: 'from-id' },
    data: { balance: { decrement: 100 } },
  });
  await tx.account.update({
    where: { id: 'to-id' },
    data: { balance: { increment: 100 } },
  });

  return { user, post };
});

// Transaction with timeout
const result = await prisma.$transaction(
  async (tx) => { /* ... */ },
  { timeout: 10000, maxWait: 5000 }
);
```

---

## Raw Queries

```typescript
// Raw query (when Prisma client can't express it)
const users = await prisma.$queryRaw`
  SELECT * FROM users
  WHERE age > ${18}
  AND email ILIKE ${'%@company.com'}
`;

// Raw execute (for DDL or non-select)
await prisma.$executeRaw`
  UPDATE users SET status = 'active' WHERE last_login > NOW() - INTERVAL '30 days'
`;
```

---

## Connection Management

```typescript
// Singleton pattern (prevents connection exhaustion in development/serverless)
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

## Migration Commands

```bash
# Create and apply migration (development)
npx prisma migrate dev --name add_user_table

# Apply pending migrations (production — no schema changes)
npx prisma migrate deploy

# Reset database (development only — drops all data)
npx prisma migrate reset

# Check migration status
npx prisma migrate status

# Generate Prisma client after schema change
npx prisma generate

# Open Prisma Studio (GUI)
npx prisma studio

# Introspect existing database
npx prisma db pull
```

---

*prisma-patterns.md v1.1.0*
