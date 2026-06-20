# Data Modeling Patterns

Advanced Prisma schema patterns: soft delete, audit trail, polymorphic relations, and performance optimizations.

---

## Soft Delete

```prisma
model Post {
  id        String    @id @default(cuid())
  title     String
  content   String?
  published Boolean   @default(false)
  deletedAt DateTime?

  @@index([deletedAt])
}
```

```typescript
// Query non-deleted records
const posts = await prisma.post.findMany({
  where: { deletedAt: null },
});

// Soft delete
await prisma.post.update({
  where: { id: 'post-id' },
  data: { deletedAt: new Date() },
});

// Restore
await prisma.post.update({
  where: { id: 'post-id' },
  data: { deletedAt: null },
});

// Global middleware for automatic soft-delete filtering
prisma.$use(async (params, next) => {
  if (params.model === 'Post') {
    if (params.action === 'findUnique' || params.action === 'findFirst') {
      params.action = 'findFirst';
      params.args.where = { ...params.args.where, deletedAt: null };
    }
    if (params.action === 'findMany') {
      params.args.where = { ...params.args.where, deletedAt: null };
    }
  }
  return next(params);
});
```

---

## Audit Trail

```prisma
model AuditLog {
  id        String   @id @default(cuid())
  tableName String
  recordId  String
  action    String   // CREATE, UPDATE, DELETE
  oldData   Json?
  newData   Json?
  userId    String
  userIp    String?
  createdAt DateTime @default(now())

  @@index([tableName, recordId])
  @@index([userId])
  @@index([createdAt])
  @@map("audit_logs")
}
```

```typescript
// Audit logging helper
async function auditedUpdate<T>(
  tx: Prisma.TransactionClient,
  model: string,
  recordId: string,
  oldData: object,
  newData: object,
  userId: string
): Promise<void> {
  await tx.auditLog.create({
    data: {
      tableName: model,
      recordId,
      action: 'UPDATE',
      oldData,
      newData,
      userId,
    },
  });
}

// Usage in a transaction
const result = await prisma.$transaction(async (tx) => {
  const old = await tx.user.findUnique({ where: { id: userId } });
  const updated = await tx.user.update({
    where: { id: userId },
    data: { name: newName },
  });
  await auditedUpdate(tx, 'User', userId, old!, updated, requestingUserId);
  return updated;
});
```

---

## Polymorphic Relations

```prisma
// Comments that can belong to Posts OR Videos
model Comment {
  id      String @id @default(cuid())
  content String

  commentableType String  // "Post" or "Video"
  commentableId   String

  @@index([commentableType, commentableId])
}

model Post {
  id       String @id @default(cuid())
  title    String
}

model Video {
  id       String @id @default(cuid())
  title    String
}
```

```typescript
// Query comments for a post
const comments = await prisma.comment.findMany({
  where: {
    commentableType: 'Post',
    commentableId: postId,
  },
});

// Create comment on any commentable
async function createComment(
  content: string,
  commentableType: 'Post' | 'Video',
  commentableId: string
) {
  return prisma.comment.create({
    data: { content, commentableType, commentableId },
  });
}
```

---

## Versioning / Optimistic Locking

```prisma
model Product {
  id       String @id @default(cuid())
  name     String
  price    Float
  version  Int    @default(0)

  @@map("products")
}
```

```typescript
// Optimistic locking — prevent concurrent overwrites
async function updateProductPrice(
  productId: string,
  newPrice: number,
  expectedVersion: number
) {
  const updated = await prisma.product.updateMany({
    where: { id: productId, version: expectedVersion },
    data: {
      price: newPrice,
      version: { increment: 1 },
    },
  });

  if (updated.count === 0) {
    throw new ConflictError('Product was modified by another request');
  }
}
```

---

## Hierarchical Data (Adjacency List)

```prisma
model Category {
  id       String     @id @default(cuid())
  name     String
  parentId String?
  parent   Category?  @relation("CategoryTree", fields: [parentId], references: [id])
  children Category[] @relation("CategoryTree")

  @@index([parentId])
}
```

```typescript
// Fetch full tree (recursive — use with depth limit)
async function getCategoryTree(parentId: string | null = null, depth = 0): Promise<any[]> {
  if (depth > 5) return []; // prevent infinite recursion

  const categories = await prisma.category.findMany({
    where: { parentId },
  });

  return Promise.all(
    categories.map(async (cat) => ({
      ...cat,
      children: await getCategoryTree(cat.id, depth + 1),
    }))
  );
}

// Flat list with path (for breadcrumbs)
async function getCategoryPath(categoryId: string): Promise<Category[]> {
  const path: Category[] = [];
  let current = await prisma.category.findUnique({ where: { id: categoryId } });

  while (current) {
    path.unshift(current);
    if (!current.parentId) break;
    current = await prisma.category.findUnique({ where: { id: current.parentId } });
  }

  return path;
}
```

---

## Multi-Tenant Pattern

```prisma
model Organization {
  id    String @id @default(cuid())
  name  String
  users User[]
  posts Post[]
}

model User {
  id     String @id @default(cuid())
  email  String
  orgId  String
  org    Organization @relation(fields: [orgId], references: [id])

  @@unique([email, orgId])
  @@index([orgId])
}

model Post {
  id    String @id @default(cuid())
  title String
  orgId String
  org   Organization @relation(fields: [orgId], references: [id])

  @@index([orgId])
}
```

```typescript
// Always scope queries by orgId
async function listUserPosts(userId: string, orgId: string) {
  return prisma.post.findMany({
    where: { orgId },  // tenant isolation
    orderBy: { createdAt: 'desc' },
  });
}
```

---

## Performance Patterns

### Select Only Needed Fields
```typescript
// BAD — fetches all fields including large ones
const users = await prisma.user.findMany();

// GOOD — only fetch what you need
const users = await prisma.user.findMany({
  select: { id: true, name: true, email: true },
});
```

### Avoid N+1 Queries
```typescript
// BAD — N+1
for (const user of users) {
  const posts = await prisma.post.findMany({ where: { userId: user.id } });
}

// GOOD — single query with include
const usersWithPosts = await prisma.user.findMany({
  include: { posts: { take: 5, orderBy: { createdAt: 'desc' } } },
});
```

### Batch Operations
```typescript
// BAD — N individual creates
for (const item of items) {
  await prisma.product.create({ data: item });
}

// GOOD — single batch
await prisma.product.createMany({
  data: items,
  skipDuplicates: true,
});
```

### Connection Pooling (PgBouncer / serverless)
```env
# Prisma with PgBouncer
DATABASE_URL="postgresql://user:pass@pgbouncer:6432/db?pgbouncer=true"
DIRECT_URL="postgresql://user:pass@postgres:5432/db"
```

```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")  // used for migrations
}
```

---

*modeling-patterns.md v1.1.0*
