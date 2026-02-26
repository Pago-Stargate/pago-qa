---
name: testrail-explore
description: Explore and summarize TestRail project structure — sections, case counts, coverage gaps. Use to understand a test suite before planning work.
---

# TestRail Explore Skill

Quickly map out a TestRail project's structure, case counts, and coverage.

## What You Need From the User

Ask the user for:
1. **Project ID** (or project name to look up)
2. **Suite ID** (if multi-suite project)
3. **Focus area** (optional) — specific section to drill into
4. **What to report**:
   - Section tree with case counts
   - Empty sections (containers vs forgotten)
   - Case field usage (which fields are populated)
   - Recent activity (cases created/updated in last N days)

## Execution

### Step 1: Get Project Info

```
get_project(project_id=X)
get_suites(project_id=X)       # for multi-suite projects
get_sections(project_id=X, suite_id=Y)
```

### Step 2: Build Section Tree

From the sections response, build a tree using `parent_id` relationships. Display with indentation:

```
Bills API (635) — 0 direct cases
├── Scanning & saving (636) — 6 cases
│   ├── Camera permission (647) — 15 cases
│   ├── Gallery permission - only iOS (648) — 12 cases
│   ├── Gallery states (649) — 14 cases
│   └── ...
├── Suppliers (637) — 0 cases (container)
│   ├── Suppliers list (653) — 19 cases
│   └── ...
└── Subscriptions (684) — 0 cases (container)
    ├── Main structure (685) — 15 cases
    └── ...
```

### Step 3: Case Counts

For each section, fetch case count:

```
GET /api/v2/get_cases/<project_id>&suite_id=<suite_id>&section_id=<id>&limit=1
```

Using `limit=1` is fast — check `size` in the response for the actual count without downloading all cases.

### Step 4: Coverage Summary

Report:
- **Total sections**: X (Y containers, Z with cases)
- **Total cases**: N
- **Deepest nesting**: L levels
- **Empty leaf sections**: list any that might be gaps
- **Largest sections**: top 5 by case count

### Step 5: Field Usage (Optional)

Sample 10-20 cases across sections and check which custom fields are populated:

```
Field                    | Populated | Empty
-------------------------|-----------|------
custom_preconds          | 85%       | 15%
custom_steps_separated   | 72%       | 28%
custom_expected          | 28%       | 72%
custom_automation_type   | 100%      | 0%
```

## API Notes

- `get_sections` returns ALL sections for a suite in one call (up to 250; paginate if more)
- `get_cases` with `limit=1` is an efficient way to get case count per section via the `size` field
- Sections have `depth` (0-based) and `parent_id` which fully describe the tree
- **Raw API returns flat custom fields** — `case["custom_preconds"]`, not nested under `"custom"`
- **MCP get_cases returns nested** — `case["custom"]["custom_preconds"]`

## Common Follow-Up Actions

After exploring, the user typically wants to:
- **Migrate**: Use `/testrail-migrate` to copy sections
- **Clean up**: Use `/testrail-audit` to check quality
- **Find & replace**: Use `/testrail-find-replace` for bulk text changes
