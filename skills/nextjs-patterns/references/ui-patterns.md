# Next.js UI Patterns Reference

## Loading States

### Automatic Loading UI (`loading.tsx`)

Create `loading.tsx` next to `page.tsx` — Next.js wraps the page in `<Suspense>` automatically.

```typescript
// app/dashboard/loading.tsx
export default function Loading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
    </div>
  );
}
```

### Skeleton Loading Pattern

```typescript
// components/UserSkeleton.tsx
export function UserSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
    </div>
  );
}

// app/users/loading.tsx
import { UserSkeleton } from '@/components/UserSkeleton';

export default function Loading() {
  return (
    <div>
      {Array.from({ length: 5 }).map((_, i) => (
        <UserSkeleton key={i} />
      ))}
    </div>
  );
}
```

---

## Error States

### Error Boundary (`error.tsx`)

Must be a Client Component. Receives `error` and `reset` props.

```typescript
// app/dashboard/error.tsx
'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div>
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

### Global Error (`global-error.tsx`)

Catches errors in the root layout. Must render `<html>` and `<body>`.

```typescript
// app/global-error.tsx
'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <h2>Something went wrong globally</h2>
        <button onClick={reset}>Try again</button>
      </body>
    </html>
  );
}
```

---

## Not Found State

### Route-Level Not Found

```typescript
// app/not-found.tsx
import Link from 'next/link';

export default function NotFound() {
  return (
    <div>
      <h2>Page Not Found</h2>
      <p>Could not find the requested resource.</p>
      <Link href="/">Return Home</Link>
    </div>
  );
}
```

### Trigger Programmatically

```typescript
// app/users/[id]/page.tsx
import { notFound } from 'next/navigation';

export default async function UserPage({ params }: PageProps) {
  const { id } = await params;
  const user = await getUser(id);

  if (!user) notFound(); // Renders the nearest not-found.tsx

  return <UserProfile user={user} />;
}
```

---

## Image Optimization

Use `next/image` for all images — automatic WebP conversion, lazy loading, size optimization.

```typescript
import Image from 'next/image';

// Fixed dimensions (local or remote)
export function Avatar({ src, alt }: { src: string; alt: string }) {
  return (
    <Image
      src={src}
      alt={alt}
      width={100}
      height={100}
      priority     // Preload above-the-fold images
    />
  );
}

// Fill container (responsive)
export function HeroBanner({ src }: { src: string }) {
  return (
    <div className="relative h-96">
      <Image
        src={src}
        alt="Hero banner"
        fill
        className="object-cover"
        sizes="100vw"
      />
    </div>
  );
}
```

Configure allowed remote domains in `next.config.js`:

```javascript
// next.config.js
module.exports = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'cdn.example.com' },
    ],
  },
};
```

---

## Fonts

Load fonts via `next/font` — zero layout shift, self-hosted automatically.

```typescript
// app/layout.tsx
import { Inter, Noto_Sans_Thai } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const notoSansThai = Noto_Sans_Thai({
  subsets: ['thai'],
  display: 'swap',
  variable: '--font-noto-thai',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${notoSansThai.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
```

---

## Metadata

### Static Metadata

```typescript
// app/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'My App',
  description: 'My app description',
  openGraph: {
    title: 'My App',
    description: 'My app description',
    images: [{ url: '/og.png' }],
  },
};
```

### Dynamic Metadata

```typescript
// app/users/[id]/page.tsx
import type { Metadata } from 'next';

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const user = await getUser(id);

  return {
    title: user ? `${user.name} | My App` : 'User Not Found',
    description: user?.bio,
  };
}
```

---

## Environment Variables

```bash
# .env.local (never commit)
DATABASE_URL=postgresql://localhost:5432/mydb
NEXTAUTH_SECRET=your-secret
NEXT_PUBLIC_API_URL=https://api.example.com   # Exposed to browser
```

```typescript
// Server-only
const dbUrl = process.env.DATABASE_URL;

// Client-accessible (prefixed NEXT_PUBLIC_)
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
```

Validate at startup using a schema library:

```typescript
// lib/env.ts
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  NEXTAUTH_SECRET: z.string().min(32),
  NEXT_PUBLIC_API_URL: z.string().url(),
});

export const env = envSchema.parse(process.env);
```

*ui-patterns.md v1.1.0*
