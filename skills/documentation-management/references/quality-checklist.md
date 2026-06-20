# Quality Checklist Reference

This file contains documentation quality checklists for pre-publish review, periodic maintenance, and coverage tracking methodology.

---

## Pre-Publish Checklist

Run before marking any document APPROVED.

### Content Quality

```
Content Quality:
- [ ] Opening paragraph states what the doc covers and who it is for
- [ ] No unexplained jargon or acronyms
- [ ] Complex concepts have concrete examples
- [ ] Code samples are minimal and tested (run them before publishing)
- [ ] No TODO, FIXME, or placeholder text remaining
- [ ] No duplicate content that exists in another doc (link instead)
```

### Technical Accuracy

```
Technical Accuracy:
- [ ] All code examples compile/execute without errors
- [ ] API specs match current implementation (check against source)
- [ ] Command-line examples work on target OS(es)
- [ ] Environment variables and config keys match actual names
- [ ] Version numbers are current (no "v2.0" if current is v3.1)
- [ ] Screenshots/diagrams reflect current UI/architecture
```

### Link Validation

```
Links:
- [ ] All internal links resolve (file exists at path)
- [ ] All anchor links resolve (heading exists in target doc)
- [ ] External links return 200 (not 301 chain or 404)
- [ ] No bare URLs — all links have descriptive text
```

### Formatting

```
Formatting:
- [ ] Single H1 at top, logical H2/H3 hierarchy (no skipped levels)
- [ ] All code blocks have language tags (```bash, ```typescript, etc.)
- [ ] Tables have header rows and readable column widths
- [ ] Consistent list style (all bullets or all numbers, not mixed)
- [ ] Version header present (title, version, status, updated)
```

---

## Periodic Review Checklists

### Monthly Review

```
Monthly (assign to doc owner):
- [ ] Scan for outdated version references (grep for old version numbers)
- [ ] Validate all external links (automated or manual)
- [ ] Review open issues tagged with "docs" label
- [ ] Update `updated` date in version header if changes made
- [ ] Check if any code changes since last review require doc updates
```

### Quarterly Audit

```
Quarterly (doc owner + reviewer):
- [ ] Full coverage audit — compare documented vs. implemented features
- [ ] Template compliance — ensure all docs follow current template versions
- [ ] Archive or delete docs marked DEPRECATED >90 days ago
- [ ] Review ADR statuses — any accepted decisions now superseded?
- [ ] Check for docs that can be merged (too many small files)
- [ ] Validate all cross-references are still accurate
```

### Pre-Release Review

```
Before each release:
- [ ] CHANGELOG.md [Unreleased] section is accurate and complete
- [ ] Breaking changes are documented with migration path
- [ ] New features have corresponding docs (no undocumented features)
- [ ] API reference matches new endpoints/fields/removed items
- [ ] README Quick Start still works with new version
- [ ] Version numbers bumped in all doc headers
```

---

## Coverage Tracking

### Coverage Formula

```
Coverage = (Documented Items / Total Items) × 100

Items to document (by category):
  API:        Public endpoints, request/response schemas, error codes
  Code:       Exported functions, classes, types with non-obvious behavior
  Config:     All environment variables, config file options
  Schema:     Database tables, fields, relationships, constraints
  Ops:        Deployment steps, runbooks, incident playbooks
```

### Coverage Report Format

```
Documentation Coverage Report
Generated: 2026-01-17
Overall: 85% (42/50 documented)

By Category:
  API Endpoints:    90% (18/20) ████████████████████░░
  Components:       75% (15/20) ████████████████░░░░░░
  Utilities:        80% (8/10)  ██████████████████░░░░
  Config Options:  100% (10/10) ██████████████████████
  DB Tables:        70% (7/10)  ████████████████░░░░░░

Undocumented (HIGH priority):
  - POST /api/users/bulk (API)
  - GET /api/reports/export (API)
  - formatCurrency() in src/utils/currency.ts (Code)

Undocumented (MEDIUM priority):
  - CACHE_TTL environment variable (Config)
  - user_sessions table (DB)
  - order_items table (DB)
```

### Tracking with grep

```bash
# Count exported functions in TypeScript
grep -r "^export function\|^export const\|^export class" src/ \
  | grep -v ".test." | wc -l

# Count documented functions (JSDoc present)
grep -r "^export function\|^export const" src/ \
  | grep -v ".test." \
  | while read line; do
      file=$(echo "$line" | cut -d: -f1)
      lineno=$(echo "$line" | cut -d: -f2)
      prev=$((lineno - 1))
      sed -n "${prev}p" "$file"
    done \
  | grep -c "^\s*\*/"

# Find undocumented API routes
grep -r "@router\.\|app\.\(get\|post\|put\|delete\|patch\)" src/routes/ \
  | grep -v ".test." \
  | grep -v "// documented"
```

### Coverage Tracking in CI

Add to CI pipeline to block merges below threshold:

```yaml
# .github/workflows/doc-coverage.yml
- name: Check documentation coverage
  run: |
    COVERAGE=$(node scripts/doc-coverage.js --format=percent)
    THRESHOLD=80
    if [ "$COVERAGE" -lt "$THRESHOLD" ]; then
      echo "Documentation coverage $COVERAGE% is below threshold $THRESHOLD%"
      exit 1
    fi
```

---

## Link Validation

### Common Issues and Fixes

| Issue | Cause | Detection | Fix |
|-------|-------|-----------|-----|
| `404 Internal` | File moved/deleted | `find` + `grep` | Update path or add redirect |
| `Anchor not found` | Heading renamed | `grep -r '#'` | Update anchor to match new heading |
| `External timeout` | Site down or moved | HTTP check | Retry; if persistent, replace or remove |
| `Case mismatch` | Wrong file casing | CI lint | Match exact filesystem casing |
| `Relative path wrong` | File moved without updating refs | `grep -r './'` | Recalculate relative path |

### Validation Script

```bash
# Check all markdown internal links exist
python3 - <<'EOF'
import os, re, sys
from pathlib import Path

docs_dir = Path("docs")
broken = []

for md_file in docs_dir.rglob("*.md"):
    content = md_file.read_text()
    links = re.findall(r'\[.*?\]\((\..*?\.md)(#.*?)?\)', content)
    for link, anchor in links:
        target = (md_file.parent / link).resolve()
        if not target.exists():
            broken.append(f"{md_file}:{link} -> NOT FOUND")

if broken:
    print("Broken internal links:")
    for b in broken: print(f"  {b}")
    sys.exit(1)
else:
    print(f"All internal links valid")
EOF

# Check for broken anchors (headings referenced but not present)
grep -rn '\[.*\](#' docs/ | while IFS=: read file lineno match; do
  anchor=$(echo "$match" | grep -o '#[^)]*')
  heading=$(echo "$anchor" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -d '#')
  echo "CHECK $file -> $anchor (heading: $heading)"
done
```

---

## Doc Debt Tracking

Track documentation debt the same way technical debt is tracked:

```markdown
## Doc Debt Register

| Item | Type | Priority | Owner | Due |
|------|------|----------|-------|-----|
| Document bulk import API | Missing | HIGH | @alice | 2026-02-01 |
| Update auth flow diagram | Outdated | MEDIUM | @bob | 2026-02-15 |
| Add runbook for DB failover | Missing | HIGH | @ops | 2026-01-31 |
| Archive v1 API docs | Cleanup | LOW | anyone | — |
```

Add doc debt items to the same issue tracker as code debt, tagged `docs-debt`.

---

*quality-checklist.md v1.1.0*
