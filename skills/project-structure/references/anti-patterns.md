# Project Structure Anti-Patterns Reference

## Deep Nesting

Keep directory depth at 5 levels or fewer. Deep nesting makes imports verbose and navigation tedious.

```
# BAD — 8 levels deep
src/modules/auth/features/login/components/forms/fields/Input.tsx

# GOOD — 4 levels
src/components/auth/LoginForm/InputField.tsx
```

Refactor strategy: collapse intermediate directories that add no logical grouping. If a folder contains only one subfolder, merge them.

---

## Type Pollution

Scattering types next to their consumers creates duplication and makes cross-feature sharing difficult.

```
# BAD — types scattered per component
src/components/Button/types.ts
src/components/Input/types.ts
src/services/auth/types.ts
src/services/user/types.ts

# GOOD — centralized by domain
src/types/
├── components.ts      # Shared component prop types
├── api.ts             # API request/response types
├── models.ts          # Domain model types
└── index.ts           # Re-exports
```

Exception: types used exclusively inside a single file may live in that file. Move them to `src/types/` only when a second consumer needs them.

---

## Feature Fragmentation

Splitting a feature's files across global folders by file type makes it hard to trace a feature end-to-end.

```
# BAD — files scattered by type
src/components/UserProfile.tsx
src/hooks/useUser.ts
src/services/userService.ts
src/types/user.ts
src/tests/user.test.ts

# GOOD — colocated by feature
src/features/user/
├── UserProfile.tsx
├── useUser.ts
├── userService.ts
├── types.ts
└── user.test.ts
```

Apply this pattern once a feature grows beyond 2–3 files. Keep shared/reusable code in `src/components/ui/`, `src/lib/`, etc.

---

## Index File Abuse (Barrel File Issues)

Barrel files clean up imports but cause problems at scale.

```typescript
// BAD — barrel over a large folder
// src/components/index.ts exports 40+ components
// → Every consumer imports the entire barrel
// → Tree-shaking breaks down
// → Slow cold start in dev

// GOOD — barrel only for small, stable collections
// src/components/ui/index.ts — 5–8 primitives (Button, Input, Select…)
export { Button } from './Button';
export { Input } from './Input';
export { Select } from './Select';
```

Rules for barrel files:
- Use only when the folder has fewer than ~15 exports.
- Avoid in folders that change frequently — every edit forces cache invalidation for all consumers.
- Never create barrel files for route segments in Next.js App Router.

---

## Import Cycle Detection

Circular imports produce runtime errors and obscure dependency graphs.

```
Symptoms:
- Import errors at runtime: "Cannot read properties of undefined"
- "Cannot access X before initialization"
- Unexplained undefined exports
```

Detection:

```bash
# Using madge (install once: npm i -g madge)
madge --circular src/

# Using eslint-plugin-import
# .eslintrc: "import/no-cycle": "error"
```

Resolution strategies:

```
1. Extract shared code to a new module
   Before: A imports B, B imports A
   After:  A imports C, B imports C (C has the shared code)

2. Dependency injection
   Pass the dependency as a parameter instead of importing it directly

3. Restructure module hierarchy
   Move the shared logic up one level in the tree
```

---

## Misused Route Groups (Next.js)

Route groups `(name)` affect layout composition, not just URL structure. Misusing them creates layout bugs.

```
# BAD — using route groups just for "organization" without thinking about layouts
app/
└── (everything)/
    ├── dashboard/
    ├── settings/
    └── profile/

# GOOD — route groups match actual layout boundaries
app/
├── (auth)/           # Shares auth layout (centered card)
│   ├── login/
│   └── register/
└── (app)/            # Shares app shell (sidebar + header)
    ├── dashboard/
    ├── settings/
    └── profile/
```

---

## Flat Structure at Scale

An entirely flat `components/` folder becomes unnavigable beyond ~20 files.

```
# BAD — flat at scale
src/components/
├── Button.tsx
├── UserProfile.tsx
├── AdminDashboard.tsx
├── LoginForm.tsx
├── ProductCard.tsx
... (40 more files)

# GOOD — grouped by purpose
src/components/
├── ui/               # Primitives — no business logic
│   ├── Button.tsx
│   ├── Input.tsx
│   └── Select.tsx
├── features/         # Feature-specific components
│   ├── auth/
│   └── products/
└── layouts/          # Page shells and wrappers
    ├── AppShell.tsx
    └── AuthLayout.tsx
```

*anti-patterns.md v1.1.0*
