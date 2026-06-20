# Next.js API Routes Reference

## Route Handler Basics

```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const page = searchParams.get('page') || '1';

  const users = await getUsers({ page: Number(page) });

  return NextResponse.json(users);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const user = await createUser(body);
  return NextResponse.json(user, { status: 201 });
}
```

Export one function per HTTP method. Supported: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`.

---

## Dynamic Route Handlers

```typescript
// app/api/users/[id]/route.ts
interface Context {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, context: Context) {
  const { id } = await context.params;
  const user = await getUser(id);

  if (!user) {
    return NextResponse.json({ error: 'User not found' }, { status: 404 });
  }

  return NextResponse.json(user);
}

export async function PUT(request: NextRequest, context: Context) {
  const { id } = await context.params;
  const body = await request.json();
  const user = await updateUser(id, body);
  return NextResponse.json(user);
}

export async function DELETE(request: NextRequest, context: Context) {
  const { id } = await context.params;
  await deleteUser(id);
  return new Response(null, { status: 204 });
}
```

---

## Request Helpers

```typescript
// Parse JSON body
const body = await request.json();

// Parse form data
const formData = await request.formData();
const name = formData.get('name') as string;

// Read cookies
const token = request.cookies.get('token')?.value;

// Read headers
const auth = request.headers.get('authorization');

// Read search params
const q = request.nextUrl.searchParams.get('q');
```

---

## Response Helpers

```typescript
// JSON response
return NextResponse.json({ data }, { status: 200 });

// Redirect
return NextResponse.redirect(new URL('/login', request.url));

// Set cookies in response
const response = NextResponse.json({ ok: true });
response.cookies.set('token', value, {
  httpOnly: true,
  secure: true,
  sameSite: 'lax',
  maxAge: 60 * 60 * 24 * 7,
});
return response;

// Plain response
return new Response('OK', { status: 200 });
return new Response(null, { status: 204 });

// Stream response
const stream = new ReadableStream({ ... });
return new Response(stream, {
  headers: { 'Content-Type': 'text/event-stream' },
});
```

---

## Server Actions

Define functions with `'use server'` to call from Client Components or forms.

```typescript
// app/actions.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;

  await db.post.create({ data: { title, content } });
  revalidatePath('/posts');
}

export async function deletePost(id: string) {
  await db.post.delete({ where: { id } });
  revalidatePath('/posts');
  redirect('/posts');
}
```

### Call from Form (Zero JS)

```typescript
import { createPost } from '../actions';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <textarea name="content" required />
      <button type="submit">Create</button>
    </form>
  );
}
```

### Call from Client Component

```typescript
'use client';

import { useTransition } from 'react';
import { createPost } from '../actions';

export function PostForm() {
  const [isPending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    startTransition(() => createPost(formData));
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="title" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create'}
      </button>
    </form>
  );
}
```

---

## Middleware

Place `middleware.ts` at the project root (same level as `app/`).

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token');

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Add headers to response
  const response = NextResponse.next();
  response.headers.set('x-pathname', request.nextUrl.pathname);
  return response;
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/api/protected/:path*',
    // Exclude static files and Next.js internals
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
```

*api-routes.md v1.1.0*
