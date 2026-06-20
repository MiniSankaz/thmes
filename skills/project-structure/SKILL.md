---
name: project-structure
description: >
  This skill should be used when the user asks to "organize a project", "set up folder structure",
  "fix naming conventions", "check module boundaries", "restructure the codebase", or needs
  guidance on project templates, naming rules, or import patterns.
version: 1.2.0
type: pattern-library
triggers:
  keywords_en: [structure, folder, organize, naming, module, refactor, reorganize, architecture]
  keywords_th: [โครงสร้าง, โฟลเดอร์, จัดระเบียบ, ชื่อไฟล์, โมดูล, รีแฟคเตอร์]
---

# Project Structure Skill

## Folder Structure Best Practices

### Core Principles
```
1. FLAT is better than nested (max 4-5 levels)
2. GROUP by feature, not by type
3. COLOCATE related files
4. EXPLICIT naming over clever naming
```

---

## Standard Project Templates

### Next.js App Router (Recommended)
```
project/
├── src/
│   ├── app/                    # App Router
│   │   ├── (auth)/            # Auth route group
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/       # Dashboard group
│   │   ├── api/               # API routes
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── ui/                # Primitives (Button, Input)
│   │   ├── features/          # Feature components
│   │   └── layouts/           # Layout components
│   ├── lib/                   # Utilities & helpers
│   ├── hooks/                 # Custom React hooks
│   ├── services/              # API clients & services
│   ├── stores/                # State management
│   ├── types/                 # TypeScript types
│   └── styles/                # Global styles
├── public/                    # Static assets
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── prisma/                    # Database schema
└── docs/                      # Documentation
```

### REST API Service
```
project/
├── src/
│   ├── controllers/           # Request handlers
│   ├── services/              # Business logic
│   ├── repositories/          # Data access layer
│   ├── models/                # Data models
│   ├── middleware/            # Express middleware
│   ├── routes/                # Route definitions
│   ├── validators/            # Request validation
│   ├── utils/                 # Utility functions
│   ├── types/                 # TypeScript types
│   └── config/                # Configuration
├── tests/
├── prisma/
└── docs/
```

### Library/Package
```
project/
├── src/
│   ├── core/                  # Core functionality
│   ├── utils/                 # Helper utilities
│   ├── types/                 # Type definitions
│   └── index.ts               # Public API exports
├── tests/
├── examples/                  # Usage examples
├── docs/
└── dist/                      # Build output
```

---

## Naming Conventions

### Files

| Type | Convention | Example | Bad Example |
|------|------------|---------|-------------|
| React Component | PascalCase | `UserProfile.tsx` | `userProfile.tsx` |
| React Hook | camelCase + use | `useAuth.ts` | `UseAuth.ts` |
| Utility | camelCase | `formatDate.ts` | `format-date.ts` |
| Constants | SCREAMING_SNAKE | `API_ENDPOINTS.ts` | `apiEndpoints.ts` |
| Types | PascalCase | `UserTypes.ts` | `userTypes.ts` |
| Test | *.test.ts | `auth.test.ts` | `auth-test.ts` |
| Config | kebab-case | `eslint.config.js` | `eslintConfig.js` |
| CSS Module | *.module.css | `Button.module.css` | `button.css` |

### Folders

| Type | Convention | Example |
|------|------------|---------|
| Feature | kebab-case | `user-management/` |
| Single Component | PascalCase | `UserProfile/` (with index) |
| Generic | kebab-case | `shared-utils/` |
| Route Group | (parentheses) | `(auth)/` |

---

## Module Boundaries

### Layer Separation
```
┌─────────────────────────────────┐
│           UI Layer              │  Components, Pages
├─────────────────────────────────┤
│        Business Layer           │  Services, Hooks
├─────────────────────────────────┤
│          Data Layer             │  Repositories, API
└─────────────────────────────────┘

Rules:
✅ UI can import Business
✅ Business can import Data
❌ Data cannot import UI
❌ Data cannot import Business
```

### Import Rules
```typescript
// GOOD - Respects layer boundaries
// In components/
import { useAuth } from '@/hooks/useAuth';
import { formatDate } from '@/lib/formatDate';

// BAD - Breaks layer boundaries
// In lib/
import { Button } from '@/components/ui/Button'; // ❌
```

### Circular Dependency Prevention
```
Signs of circular dependency:
- Import errors at runtime
- Undefined exports
- "Cannot access before initialization"

Solutions:
1. Extract shared code to new module
2. Use dependency injection
3. Restructure module hierarchy
```

---

## Index Files (Barrel Exports)

### When to Use
```typescript
// components/ui/index.ts
export { Button } from './Button';
export { Input } from './Input';
export { Select } from './Select';

// Usage
import { Button, Input, Select } from '@/components/ui';
```

### When NOT to Use
```
❌ Large folders (>20 files) - causes bundle bloat
❌ Frequently changing files
❌ When tree-shaking is important
```

---

## Quick Validation Checklist

```
Structure Health Check:
- [ ] Max folder depth ≤ 5
- [ ] No circular dependencies
- [ ] Consistent naming conventions
- [ ] Required folders exist (src, tests)
- [ ] Index files where appropriate
- [ ] No orphaned files
- [ ] Layer boundaries respected
```

---

## Configuration

### structure-config.yaml
```yaml
project:
  type: nextjs
  max_depth: 5

naming:
  components: PascalCase
  hooks: camelCase
  utils: camelCase
  folders: kebab-case

required:
  - src
  - tests
  - docs

ignore:
  - node_modules
  - .next
  - dist
```

---

## Additional Resources

For detailed patterns, consult:
- **`references/anti-patterns.md`** — Deep nesting, type pollution, feature fragmentation, barrel file abuse, import cycle detection, flat-structure-at-scale, misused route groups

---

*Project Structure Skill v1.2.0*
*ใช้เพื่อจัดระเบียบ codebase อย่างมีมาตรฐาน*
