---
name: nextjs-patterns
description: >
  This skill should be used when the user asks to "create a Next.js page", "add an API route",
  "use server components", "set up layouts", "implement server actions", "add middleware",
  or needs guidance on App Router patterns, data fetching, or Next.js project structure.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [nextjs, next, react, component, page, app router, server component, use client]
  keywords_th: [เน็กซ์, รีแอค, คอมโพเนนต์, หน้า, เพจ, รีแอกต์]
---

# Next.js Patterns Skill

## Next.js Philosophy (App Router)

```
✅ Server Components by default
✅ Use 'use client' only when needed
✅ Collocate related files
✅ Leverage file-based routing
```

---

## Project Structure

```
app/
├── layout.tsx              # Root layout
├── page.tsx                # Home page (/)
├── loading.tsx             # Loading UI
├── error.tsx               # Error UI
├── not-found.tsx           # 404 page
├── globals.css             # Global styles
│
├── (marketing)/            # Route group (no URL impact)
│   ├── about/
│   │   └── page.tsx        # /about
│   └── contact/
│       └── page.tsx        # /contact
│
├── dashboard/
│   ├── layout.tsx          # Dashboard layout
│   ├── page.tsx            # /dashboard
│   └── settings/
│       └── page.tsx        # /dashboard/settings
│
├── api/
│   └── users/
│       └── route.ts        # API endpoint
│
└── _components/            # Private folder (not routed)
    └── Button.tsx

components/                  # Shared components
├── ui/
│   ├── Button.tsx
│   └── Input.tsx
└── forms/
    └── LoginForm.tsx

lib/                        # Utilities
├── utils.ts
├── db.ts
└── auth.ts
```

---

## Page Components

### Basic Page (Server Component)
```typescript
// app/users/page.tsx
import { getUsers } from '@/lib/db';

export default async function UsersPage() {
  const users = await getUsers();

  return (
    <div>
      <h1>Users</h1>
      <ul>
        {users.map(user => (
          <li key={user.id}>{user.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Page with Params
```typescript
// app/users/[id]/page.tsx
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function UserPage({ params }: PageProps) {
  const { id } = await params;
  const user = await getUser(id);

  if (!user) {
    notFound();
  }

  return <UserProfile user={user} />;
}

// Generate static params
export async function generateStaticParams() {
  const users = await getUsers();
  return users.map(user => ({ id: user.id }));
}
```

### Page with Search Params
```typescript
// app/search/page.tsx
interface PageProps {
  searchParams: Promise<{ q?: string; page?: string }>;
}

export default async function SearchPage({ searchParams }: PageProps) {
  const { q, page } = await searchParams;
  const results = await search(q, Number(page) || 1);

  return <SearchResults results={results} />;
}
```

---

## Client Components

```typescript
// components/Counter.tsx
'use client';

import { useState } from 'react';

export function Counter() {
  const [count, setCount] = useState(0);

  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  );
}
```

### When to use 'use client'
- Event handlers (onClick, onChange)
- useState, useEffect, useRef
- Browser APIs (localStorage, window)
- Third-party client libraries

---

## Layouts

### Root Layout
```typescript
// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'My App',
  description: 'My app description',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav>Navigation</nav>
        <main>{children}</main>
        <footer>Footer</footer>
      </body>
    </html>
  );
}
```

### Nested Layout
```typescript
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="dashboard">
      <Sidebar />
      <div className="content">{children}</div>
    </div>
  );
}
```

---

## Additional Resources

For detailed patterns, consult:
- **`references/data-fetching.md`** — Server component fetch, caching strategies (force-cache, no-store, ISR), tag-based revalidation, parallel fetching, streaming with Suspense, ORM caching
- **`references/api-routes.md`** — Route handler patterns, dynamic routes, request/response helpers, Server Actions (form + client usage), middleware
- **`references/ui-patterns.md`** — Loading/error/not-found states, skeleton patterns, image optimization, fonts, metadata (static + dynamic), environment variable validation

---

*Next.js Patterns Skill v1.2.0*
