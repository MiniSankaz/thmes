# tsconfig.json Recommended Template

## Full Template

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## Option Explanations

### Output Target

| Option | Value | Reason |
|--------|-------|--------|
| `target` | `ES2022` | Modern JS with native async/await, optional chaining, class fields |
| `module` | `ESNext` | Preserve ESM imports; bundler handles transformation |
| `moduleResolution` | `bundler` | Matches Vite/webpack/Turbopack resolution — use `node16` for pure Node.js |

### Strictness

| Option | Explanation |
|--------|-------------|
| `strict` | Enables all strict checks: `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `alwaysStrict` |
| `noUncheckedIndexedAccess` | Array/object index access returns `T \| undefined`, not `T` — forces bounds checking |
| `noImplicitReturns` | Functions must explicitly return in all code paths |
| `noFallthroughCasesInSwitch` | Each `case` must end with `break`, `return`, or `throw` |

### Interop

| Option | Explanation |
|--------|-------------|
| `skipLibCheck` | Skip type-checking `.d.ts` files — faster builds, avoids third-party declaration errors |
| `esModuleInterop` | Allow `import React from 'react'` instead of `import * as React` |
| `resolveJsonModule` | Allow `import data from './data.json'` with inferred types |
| `isolatedModules` | Each file must be a self-contained module — required for Babel/SWC/esbuild transpilation |

### Output

| Option | Explanation |
|--------|-------------|
| `declaration` | Generate `.d.ts` files alongside `.js` — required when publishing a library |
| `declarationMap` | Generate `.d.ts.map` files for source navigation in IDEs |
| `sourceMap` | Generate `.js.map` for debugger source mapping |
| `outDir` | Write compiled output to `./dist` |
| `rootDir` | Treat `./src` as the root — preserves directory structure in `outDir` |

---

## Variant: Next.js App Router

Next.js generates its own `tsconfig.json`. The key differences:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "paths": {
      "@/*": ["./src/*"]
    },
    "plugins": [{ "name": "next" }]
  }
}
```

- `jsx: "preserve"` — Next.js handles JSX transformation; do not set `react-jsx` manually.
- `paths` — Configure path aliases to match `next.config.js` `alias` or `baseUrl`.
- `plugins: [{ "name": "next" }]` — Enables Next.js IDE completions (e.g., metadata types).

---

## Variant: Node.js Service (CommonJS)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "moduleResolution": "node",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src"
  }
}
```

Use `module: "commonjs"` + `moduleResolution: "node"` for Node.js services that do not use a bundler.

*tsconfig-template.md v1.1.0*
