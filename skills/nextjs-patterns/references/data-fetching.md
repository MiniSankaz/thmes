# Next.js Data Fetching Reference

## Server Component Fetch

Fetch directly inside a Server Component — no useEffect, no loading state boilerplate.

```typescript
// app/users/page.tsx
async function getUsers() {
  const res = await fetch('https://api.example.com/users', {
    cache: 'no-store', // Always fetch fresh
  });

  if (!res.ok) {
    throw new Error('Failed to fetch users');
  }

  return res.json();
}

export default async function UsersPage() {
  const users = await getUsers();
  return <UserList users={users} />;
}
```

---

## Caching Strategies

### `force-cache` (Default — Static)

Cache the response indefinitely. Equivalent to SSG.

```typescript
const res = await fetch('https://api.example.com/config', {
  cache: 'force-cache',
});
```

### `no-store` (Dynamic)

Skip the cache on every request. Equivalent to SSR.

```typescript
const res = await fetch('https://api.example.com/live-data', {
  cache: 'no-store',
});
```

### Time-Based Revalidation (ISR)

Serve cached data, revalidate in the background after N seconds.

```typescript
const res = await fetch('https://api.example.com/posts', {
  next: { revalidate: 3600 }, // Revalidate every hour
});
```

### Tag-Based Revalidation (On-Demand ISR)

Tag cached responses, then invalidate by tag from a Route Handler or Server Action.

```typescript
// Fetch with tag
const res = await fetch('https://api.example.com/posts', {
  next: { tags: ['posts'] },
});

// Invalidate from API route or Server Action
import { revalidatePath, revalidateTag } from 'next/cache';

export async function POST() {
  revalidateTag('posts');         // Revalidate all requests tagged 'posts'
  revalidatePath('/posts');       // Revalidate all requests for /posts path
  return Response.json({ ok: true });
}
```

---

## Parallel Data Fetching

Start multiple fetches simultaneously to avoid waterfall latency.

```typescript
export default async function DashboardPage() {
  // Launch both fetches in parallel — do NOT await sequentially
  const [usersPromise, statsPromise] = [
    getUsers(),
    getStats(),
  ];

  const [users, stats] = await Promise.all([usersPromise, statsPromise]);

  return (
    <div>
      <UserCount count={users.length} />
      <StatsPanel stats={stats} />
    </div>
  );
}
```

---

## Streaming with Suspense

Use `<Suspense>` to stream slow data without blocking the full page.

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react';
import { UserList } from '@/components/UserList';
import { SlowWidget } from '@/components/SlowWidget';

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      {/* UserList renders immediately */}
      <Suspense fallback={<p>Loading users...</p>}>
        <UserList />
      </Suspense>
      {/* SlowWidget streams in later */}
      <Suspense fallback={<p>Loading stats...</p>}>
        <SlowWidget />
      </Suspense>
    </div>
  );
}

// components/UserList.tsx — async Server Component
export async function UserList() {
  const users = await getUsers(); // slow fetch inside Suspense boundary
  return <ul>{users.map(u => <li key={u.id}>{u.name}</li>)}</ul>;
}
```

---

## ORM / Database (No fetch)

Call database or ORM directly from Server Components — no API round-trip needed.

```typescript
// app/users/page.tsx
import { prisma } from '@/lib/db';

export default async function UsersPage() {
  const users = await prisma.user.findMany({
    orderBy: { createdAt: 'desc' },
    take: 20,
  });

  return <UserList users={users} />;
}
```

Use `unstable_cache` to cache ORM results similarly to `fetch` cache:

```typescript
import { unstable_cache } from 'next/cache';

const getCachedUsers = unstable_cache(
  async () => prisma.user.findMany(),
  ['users'],
  { revalidate: 60, tags: ['users'] }
);
```

*data-fetching.md v1.1.0*
