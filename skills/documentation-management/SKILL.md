---
name: documentation-management
description: >
  This skill should be used when the user asks to "manage documentation", "update the changelog",
  "version a document", "create an ADR", "check doc coverage", or needs guidance on document
  lifecycle, versioning, cross-references, or documentation templates.
version: 1.1.0
type: adapter
triggers:
  keywords_en: [docs, documentation, version, changelog, release, link, readme, guide]
  keywords_th: [เอกสาร, อัพเดท, เวอร์ชัน, ลิงก์, คู่มือ, รีดมี]
---

# Documentation Management Skill

## Documentation Philosophy

Treat documentation as code: version it, review it, test it. Keep docs colocated with the code they describe. Maintain a single source of truth — link to existing content rather than duplicating it. Update docs in the same PR as the code change that makes them necessary.

---

## Document Lifecycle

### Status Flow

```
DRAFT → REVIEW → APPROVED → DEPRECATED → ARCHIVED
  ↑        ↓
  └────────┘  (revisions needed)
```

### Status Definitions

| Status | Meaning | Actions Allowed |
|--------|---------|-----------------|
| DRAFT | Work in progress | Full edit access |
| REVIEW | Awaiting approval | Comments only |
| APPROVED | Published | Minor fixes only |
| DEPRECATED | Outdated, replacement exists | Add redirect notice |
| ARCHIVED | Historical record | Read-only |

**Transition rules:**
- Move DRAFT → REVIEW when content is complete and code is merged.
- Move REVIEW → APPROVED after at least one reviewer signs off.
- Move APPROVED → DEPRECATED when a replacement document exists; always include a link to the replacement.
- Move DEPRECATED → ARCHIVED after 90 days or when the deprecated version is no longer referenced.

---

## Version Numbering

Apply semantic versioning to every document. Increment the version in the header on every meaningful change.

```
MAJOR.MINOR.PATCH

MAJOR (1.0.0 → 2.0.0):
  - Complete rewrite
  - Breaking structural changes that invalidate prior section links
  - Major scope overhaul

MINOR (1.0.0 → 1.1.0):
  - New sections added
  - Significant content updates
  - New examples or templates

PATCH (1.0.0 → 1.0.1):
  - Typo fixes
  - Clarifications without new information
  - Minor updates to keep examples current
```

### Version Header

Place this frontmatter block at the top of every managed document:

```markdown
---
title: Document Title
version: 1.2.0
status: approved
created: 2026-01-01
updated: 2026-01-17
author: Author Name
reviewers: [Reviewer 1, Reviewer 2]
---
```

---

## Cross-Reference Patterns

### Internal Links

Use relative paths. Prefer specific anchors over linking to the top of a long document.

```markdown
[Related Doc](./related.md)
[Parent Section](../overview.md)
[Specific Section](./doc.md#section-name)
```

### Code References

Reference files and lines directly so readers can navigate to the implementation.

```markdown
See implementation in `src/services/auth.ts`
The main logic is at `src/services/auth.ts:45-60`
See `authenticateUser()` in `src/services/auth.ts`
```

### External Links

Always use descriptive link text; never bare URLs in prose.

```markdown
[React Documentation](https://react.dev/reference)

<!-- Reference-style for links used more than once -->
[Next.js][nextjs] is a React framework.
[nextjs]: https://nextjs.org
```

### Link Validation

Run validation before publishing and in CI:

```bash
# Find internal links pointing to missing files
find docs -name "*.md" -exec grep -l '\[.*\](\./' {} \;

# Find anchor references
grep -r '\[.*\](#' docs/
```

Common issues: file renamed without updating refs, heading text changed invalidating anchors, case mismatch on case-sensitive filesystems.

---

## Quick Reference: Doc File Locations

```
project/
├── README.md                    # Project overview
├── CONTRIBUTING.md              # How to contribute
├── CHANGELOG.md                 # Version history
├── docs/
│   ├── index.md                # Docs home
│   ├── getting-started.md
│   ├── api/                    # API reference
│   ├── guides/                 # How-to guides
│   └── adr/                    # Architecture Decision Records
└── .github/
    └── PULL_REQUEST_TEMPLATE.md
```

### File Naming Convention

```
kebab-case.md           # General docs
UPPERCASE.md            # Root-level standards (README, CONTRIBUTING)
adr-001-title.md        # Numbered records (zero-padded)
2026-01-17-title.md     # Dated content (blog posts, incident reports)
```

---

## Best Practices

Start with "what" before "how" — readers need context before instructions. Use active voice and imperative mood in procedures ("Run `npm install`", not "You should run"). Keep paragraphs to 3–4 sentences maximum; use headings aggressively so readers can scan.

Update docs in the same PR as code changes. Assign a named owner to each doc section so reviews have a clear assignee. Set up automated link checking in CI to catch broken references before they reach main. Track documentation debt in the same issue tracker as code debt, tagged `docs-debt`.

Do not:
- Leave TODO comments in APPROVED documents
- Duplicate content that exists elsewhere — link instead
- Use outdated examples that no longer reflect current code
- Assume reader knowledge — define terms on first use

---

## Additional Resources

For detailed patterns, consult:
- **`references/templates.md`** — README, API endpoint, ADR, and CONTRIBUTING templates ready to copy
- **`references/changelog-format.md`** — Full Keep a Changelog format, commit-to-section mapping, version bump rules, and release workflow
- **`references/quality-checklist.md`** — Pre-publish checklist, periodic review schedule, coverage tracking formula and scripts, link validation tooling

---

*Documentation Management Skill v1.1.0*
*เอกสารที่ดีคือของขวัญสำหรับทีมในอนาคต*
