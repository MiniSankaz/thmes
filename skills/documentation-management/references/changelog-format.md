# Changelog Format Reference

This file covers the Keep a Changelog standard in full, commit-type-to-section mapping, versioning conventions, and release workflow.

---

## Keep a Changelog Standard

Full format with all sections:

```markdown
# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- New endpoint `GET /api/users/export` for bulk user export (#234)
- Support for OAuth2 PKCE flow in authentication module

### Changed
- `POST /api/orders` now returns full order object instead of ID only
- Rate limit increased from 100 to 200 requests/minute

### Deprecated
- `GET /api/v1/users` — use `GET /api/v2/users` instead, removal in v4.0.0
- `formatDate()` utility — use `date-fns` directly

### Removed
- Removed legacy XML response format (deprecated in v2.0.0)
- Removed `userId` field from `OrderResponse` (use `user.id`)

### Fixed
- Auth token refresh now handles concurrent requests correctly (#456)
- Pagination returns correct `total` count when filters are applied (#489)

### Security
- Upgraded `jsonwebtoken` to v9.0.2 (CVE-2022-23529)
- Added CSRF protection to all state-mutating endpoints

## [3.1.0] - 2026-01-17

### Added
- Background job queue for email notifications
- `DELETE /api/users/:id/sessions` to revoke all sessions

### Changed
- Improved error messages to include field-level details

### Fixed
- Memory leak in WebSocket connection handler (#412)

## [3.0.0] - 2025-12-01

### Breaking Changes
- API v1 (`/api/v1/`) fully removed — migrate to v2
- Authentication now requires `X-Client-Version` header
- `UserResponse.name` split into `firstName` and `lastName`

### Added
- Complete API v2 with consistent envelope format
- GraphQL endpoint at `/api/graphql`

## [2.5.0] - 2025-10-15
...
```

---

## Commit Type to Changelog Section Mapping

| Commit Prefix | Changelog Section | Include? | Notes |
|---------------|-------------------|----------|-------|
| `feat:` | **Added** | Yes | New features, endpoints, options |
| `feat!:` or `BREAKING CHANGE:` | **Breaking Changes** | Yes | Appears at top of version block |
| `fix:` | **Fixed** | Yes | Bug fixes, incorrect behavior |
| `security:` | **Security** | Yes | CVE patches, hardening |
| `perf:` | **Changed** | Yes | If user-observable behavior changes |
| `refactor:` | **Changed** | Sometimes | Only if it changes external behavior |
| `deprecate:` | **Deprecated** | Yes | Sunset notices |
| `remove:` | **Removed** | Yes | Deletion of deprecated features |
| `docs:` | — | No | Internal documentation changes |
| `chore:` | — | No | Dependency updates, CI, tooling |
| `test:` | — | No | Test-only changes |
| `style:` | — | No | Formatting only |

### Filtering Script

Extract changelog-worthy commits since last tag:

```bash
# Get commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline \
  | grep -E '^[a-f0-9]+ (feat|fix|security|perf|deprecate|remove|refactor)' \
  | sort

# Group by type
git log $(git describe --tags --abbrev=0)..HEAD --pretty=format:"%s" \
  | grep -E '^(feat|fix|security)' \
  | awk -F: '{print $1": "$2}' \
  | sort
```

---

## Version Bump Decision Table

| Change Type | Example | Bump |
|-------------|---------|------|
| New feature (backward compatible) | Add endpoint | MINOR |
| Bug fix (backward compatible) | Fix return value | PATCH |
| Breaking API change | Remove field | MAJOR |
| Security patch | CVE fix | PATCH or MINOR |
| Deprecation notice only | Mark field deprecated | MINOR |
| Remove deprecated feature | Delete old endpoint | MAJOR |
| Performance improvement | No behavior change | PATCH |
| Documentation only | No release needed | — |

### Pre-release Tags

```
1.0.0-alpha.1   # Early development, unstable API
1.0.0-beta.2    # Feature complete, testing phase
1.0.0-rc.1      # Release candidate, bug fixes only
```

---

## Release Workflow

### Step 1: Prepare CHANGELOG.md

```bash
# 1. Move [Unreleased] section to new version block
# 2. Add release date
# 3. Create new empty [Unreleased] section
```

Before:
```markdown
## [Unreleased]
### Added
- Feature X
```

After:
```markdown
## [Unreleased]

## [2.1.0] - 2026-01-17
### Added
- Feature X
```

### Step 2: Update Version References

```bash
# Update package.json
npm version minor  # or major/patch

# Update version in source files
sed -i 's/version: "2.0.0"/version: "2.1.0"/' src/config.ts
```

### Step 3: Tag and Release

```bash
git add CHANGELOG.md package.json
git commit -m "chore: release v2.1.0"
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin main --tags
```

### Step 4: Generate Release Notes from CHANGELOG

```bash
# Extract section for specific version
awk '/^## \[2\.1\.0\]/,/^## \[/' CHANGELOG.md \
  | head -n -1  # Remove trailing ## line
```

---

## Changelog Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| "Various bug fixes" | Unhelpful — what was fixed? | List specific issues with ticket numbers |
| "Updated dependencies" | Noise unless security-relevant | Skip unless CVE or breaking change |
| "Refactored X" | Internal concern | Only include if behavior changes |
| Missing issue links | No traceability | Always add `(#NNN)` for tracked issues |
| Reverse chronological body | Hard to scan | Keep newest version at top |
| No "Unreleased" section | Accumulating changes get lost | Always maintain `[Unreleased]` block |
| Breaking change buried in "Changed" | Users miss migration need | Use dedicated "Breaking Changes" header |

---

## Multi-Package Monorepo Changelogs

For monorepos with independent versioning:

```
packages/
  api/CHANGELOG.md         # @org/api versioned independently
  ui/CHANGELOG.md          # @org/ui versioned independently
CHANGELOG.md               # Top-level: cross-cutting changes only
```

Tooling options:
- `changesets` — explicit change tracking per package
- `lerna` — conventional commits auto-generation
- `release-it` — single-package automation

---

*changelog-format.md v1.1.0*
