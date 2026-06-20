---
name: typescript-conventions
description: >
  This skill should be used when the user asks to "write TypeScript", "define types",
  "create an interface", "use generics", "configure tsconfig", or needs guidance on
  TypeScript conventions, utility types, type guards, or strict mode settings.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [typescript, type, interface, generic, ts, tsx, typing, tsconfig]
  keywords_th: [ไทป์สคริปต์, ไทป์, อินเตอร์เฟส, เจเนอริก, ชนิดข้อมูล]
---

# TypeScript Conventions Skill

## TypeScript Philosophy

```
✅ Use strict mode always
✅ Prefer type inference where possible
✅ Use interfaces for objects, types for unions
✅ Avoid any - use unknown instead
```

---

## Basic Types

```typescript
// Primitives
const name: string = "John";
const age: number = 30;
const active: boolean = true;
const nothing: null = null;
const notDefined: undefined = undefined;

// Arrays
const numbers: number[] = [1, 2, 3];
const names: Array<string> = ["a", "b"];

// Tuples
const pair: [string, number] = ["age", 30];

// Objects
const user: { name: string; age: number } = { name: "John", age: 30 };
```

---

## Interfaces vs Types

### Use Interfaces for Objects
```typescript
// Objects - use interface
interface User {
  id: string;
  name: string;
  email: string;
  createdAt: Date;
}

// Extending interfaces
interface Admin extends User {
  role: 'admin';
  permissions: string[];
}
```

### Use Types for Unions/Aliases
```typescript
// Union types
type Status = 'pending' | 'active' | 'inactive';
type Result<T> = T | Error;

// Aliases
type ID = string | number;
type Callback = (data: unknown) => void;
```

---

## Function Types

```typescript
// Function declaration
function greet(name: string): string {
  return `Hello, ${name}`;
}

// Arrow function
const greet = (name: string): string => `Hello, ${name}`;

// Optional parameters
function greet(name: string, greeting?: string): string {
  return `${greeting ?? 'Hello'}, ${name}`;
}

// Default parameters
function greet(name: string, greeting = 'Hello'): string {
  return `${greeting}, ${name}`;
}

// Rest parameters
function sum(...numbers: number[]): number {
  return numbers.reduce((a, b) => a + b, 0);
}

// Function type
type GreetFn = (name: string) => string;
```

---

## Generics

### Basic Generics
```typescript
// Generic function
function identity<T>(value: T): T {
  return value;
}

// Generic interface
interface Response<T> {
  data: T;
  status: number;
  message: string;
}

// Generic type
type AsyncResult<T> = Promise<Response<T>>;

// Multiple type parameters
function pair<K, V>(key: K, value: V): [K, V] {
  return [key, value];
}
```

### Constraints
```typescript
// Extends constraint
function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}

// keyof constraint
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

---

## Async Types

```typescript
// Promise types
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/users/${id}`);
  return response.json();
}

// Async function type
type FetchFn<T> = (id: string) => Promise<T>;
```

---

## Module Types

```typescript
// Export types
export interface User { ... }
export type Status = 'active' | 'inactive';

// Import types
import type { User, Status } from './types';

// Re-export
export type { User } from './user';
export { User as UserType } from './user';
```

---

## Best Practices

### DO
```typescript
// Use strict mode
// tsconfig.json: "strict": true

// Use const assertions
const STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
} as const;

// Use unknown over any
function parseJSON(json: string): unknown {
  return JSON.parse(json);
}

// Use readonly for immutability
interface Config {
  readonly apiUrl: string;
  readonly timeout: number;
}
```

### DON'T
```typescript
// Don't use any
function bad(data: any) { } // BAD

// Don't use type assertions unnecessarily
const user = data as User; // BAD if not validated

// Don't use non-null assertion carelessly
const name = user!.name; // BAD - might be null
```

---

## Additional Resources

For detailed patterns, consult:
- **`references/utility-types.md`** — Full utility types reference (Partial, Pick, Omit, Extract, ReturnType, Awaited, conditional types), type guards (typeof, instanceof, in, custom predicates, assertion functions), discriminated unions
- **`references/tsconfig-template.md`** — Recommended tsconfig.json template with per-option explanations, plus Next.js App Router and Node.js CommonJS variants

---

*TypeScript Conventions Skill v1.2.0*
