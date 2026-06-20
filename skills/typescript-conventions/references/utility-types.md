# TypeScript Utility Types & Type Guards Reference

## Utility Types

### Structural Transformations

```typescript
// Partial — make all properties optional
type PartialUser = Partial<User>;

// Required — make all properties required
type RequiredUser = Required<User>;

// Readonly — make all properties readonly
type ReadonlyUser = Readonly<User>;
```

### Property Selection

```typescript
// Pick — select specific properties
type UserPreview = Pick<User, 'id' | 'name'>;

// Omit — exclude specific properties
type UserWithoutEmail = Omit<User, 'email'>;

// Record — construct a key-value object type
type UserMap = Record<string, User>;
type StatusLabels = Record<Status, string>;
```

### Set Operations on Union Types

```typescript
type Status = 'pending' | 'active' | 'inactive' | 'archived';

// Extract — keep union members that are assignable to the filter
type LiveStatus = Extract<Status, 'pending' | 'active'>;
// → 'pending' | 'active'

// Exclude — remove union members that are assignable to the filter
type NonActive = Exclude<Status, 'active'>;
// → 'pending' | 'inactive' | 'archived'

// NonNullable — remove null and undefined from a type
type DefinedValue = NonNullable<string | null | undefined>;
// → string
```

### Function Introspection

```typescript
// ReturnType — extract a function's return type
type GreetResult = ReturnType<typeof greet>;

// Parameters — extract a function's parameter tuple
type GreetParams = Parameters<typeof greet>;

// ConstructorParameters — extract constructor parameter tuple
type DateParams = ConstructorParameters<typeof Date>;

// InstanceType — extract the instance type from a constructor
type DateInstance = InstanceType<typeof Date>;

// Awaited — unwrap a Promise type recursively
type UserData = Awaited<Promise<User>>;
// → User
```

---

## Conditional Types

```typescript
// Basic conditional
type IsString<T> = T extends string ? true : false;

// Infer — extract types from within a conditional
type UnpackArray<T> = T extends Array<infer Item> ? Item : T;
type NumberItem = UnpackArray<number[]>; // → number
type StringSelf = UnpackArray<string>;   // → string

// Distributive conditional (distributes over union)
type ToArray<T> = T extends unknown ? T[] : never;
type StringOrNumberArray = ToArray<string | number>;
// → string[] | number[]
```

---

## Type Guards

### `typeof` Guard

```typescript
function process(value: string | number) {
  if (typeof value === 'string') {
    return value.toUpperCase(); // value: string
  }
  return value * 2; // value: number
}
```

### `instanceof` Guard

```typescript
function handleError(error: Error | string) {
  if (error instanceof Error) {
    return error.message; // error: Error
  }
  return error; // error: string
}
```

### `in` Operator Guard

```typescript
interface Admin {
  role: 'admin';
  permissions: string[];
}

interface User {
  name: string;
}

function describeUser(person: Admin | User) {
  if ('permissions' in person) {
    return `Admin with ${person.permissions.length} permissions`;
  }
  return `User: ${person.name}`;
}
```

### Custom Type Predicate

```typescript
interface Dog { bark(): void; }
interface Cat { meow(): void; }

function isDog(animal: Dog | Cat): animal is Dog {
  return 'bark' in animal;
}

// Usage
function makeNoise(animal: Dog | Cat) {
  if (isDog(animal)) {
    animal.bark(); // animal: Dog
  } else {
    animal.meow(); // animal: Cat
  }
}
```

### Assertion Function

```typescript
function assertDefined<T>(value: T | null | undefined, name: string): asserts value is T {
  if (value == null) {
    throw new Error(`${name} must be defined`);
  }
}

// Usage — narrows type after call
assertDefined(user, 'user');
console.log(user.name); // user: User (not null/undefined)
```

---

## Discriminated Unions

Define a shared literal discriminant field to allow exhaustive narrowing.

```typescript
interface SuccessResult {
  type: 'success';
  data: unknown;
}

interface ErrorResult {
  type: 'error';
  error: Error;
}

interface LoadingResult {
  type: 'loading';
}

type Result = SuccessResult | ErrorResult | LoadingResult;

function handle(result: Result) {
  switch (result.type) {
    case 'success':
      return result.data; // result: SuccessResult
    case 'error':
      throw result.error; // result: ErrorResult
    case 'loading':
      return null;        // result: LoadingResult
    default:
      // Exhaustiveness check — compile error if a variant is unhandled
      const _exhaustive: never = result;
      return _exhaustive;
  }
}
```

*utility-types.md v1.1.0*
