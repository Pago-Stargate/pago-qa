---
name: testrail-migrate
description: Migrate/copy TestRail test cases between sections with full hierarchy and optional text replacements. Use when moving, cloning, or forking test suites.
---

# TestRail Migration Skill

Migrate test cases from one TestRail section to another, preserving the full section hierarchy and all case content.

## What You Need From the User

Ask the user for:
1. **Source section** — the section ID (or name + project) to copy FROM
2. **Target parent section** — the section ID to copy INTO
3. **Project ID and Suite ID** — for API calls
4. **Exclusions** — any subsections to skip (by ID or name)
5. **Renames** — any section names to change (e.g., "BCR" → "Partner")
6. **Text replacements** — any find/replace pairs to apply to case content (titles, preconditions, expected results, steps)
7. **Credentials** — TestRail URL and API credentials (email:api_key)

## Execution Steps

### Step 1: Discover Source Structure

Use the MCP `get_sections` tool to fetch all sections for the project/suite:

```
get_sections(project_id=X, suite_id=Y)
```

Filter to find all sections under the source parent. Build a tree (parent → children) and identify:
- Total sections to create
- Sections to exclude
- Sections to rename

Present the plan to the user for confirmation before proceeding.

### Step 2: Create Section Hierarchy

**There is no MCP tool for creating sections.** Use `curl` via Bash:

```bash
curl -s -X POST "https://<instance>.testrail.io/index.php?/api/v2/add_section/<project_id>" \
  -H "Content-Type: application/json" \
  -u "<email>:<api_key>" \
  -d '{"name": "<NAME>", "parent_id": <PARENT_ID>, "suite_id": <SUITE_ID>}'
```

**Create in BFS order** (all Level 1 first, then Level 2, etc.) because children need their parent's new ID.

Build and maintain a mapping: `old_section_id → new_section_id`.

### Step 3: Fetch and Copy Cases

For each section in the mapping (skip container-only sections with 0 cases):

1. **Fetch cases** using the raw REST API (not MCP), because the raw API returns **flat custom fields** at the top level:

```bash
GET /api/v2/get_cases/<project_id>&suite_id=<suite_id>&section_id=<old_id>&limit=250&offset=0
```

Custom fields in the response are at the TOP LEVEL: `case["custom_preconds"]`, `case["custom_steps_separated"]`, etc. — **NOT** nested under a `"custom"` key. The MCP tool wraps them, but raw API does not.

2. **Create each case** via curl or the raw API:

```bash
POST /api/v2/add_case/<new_section_id>
```

### Critical: template_id

- **`template_id: 2`** (Test Case - Steps) — use when the case has `custom_steps_separated`. This template does NOT require `custom_expected`.
- **`template_id: 1`** (Test Case - Text) — use when the case has no steps. This template REQUIRES `custom_expected` (send `"N/A"` if the source is null/empty).

Using the wrong template causes `"Field :custom_expected is a required field"` errors.

### Payload Structure

```json
{
  "title": "...",
  "template_id": 2,
  "type_id": 7,
  "priority_id": 2,
  "custom_automation_type": 0,
  "custom_preconds": "...",
  "custom_steps_separated": [
    {"content": "step text", "expected": "expected result"}
  ]
}
```

Fields to preserve: `title`, `type_id`, `priority_id`, `refs`, `custom_automation_type`, `custom_preconds`, `custom_expected`, `custom_steps_separated`, `custom_testrail_bdd_scenario`, `custom_mission`, `custom_goals`.

### Step 4: Apply Text Replacements

When copying cases from sections that need text replacement:
- Apply replacements to: `title`, `custom_preconds`, `custom_expected`, `custom_steps_separated[].content`, `custom_steps_separated[].expected`, `refs`
- **Protect URLs** inside `href=""` attributes — use a placeholder approach:
  1. Extract all `href="..."` strings and replace with placeholders
  2. Run text replacements
  3. Restore original href strings

### Step 5: Verify

1. Count new sections under target parent — should match expected count
2. Spot-check case counts in a few sections (old vs new)
3. For renamed sections, verify text replacements in case content
4. Confirm excluded sections have no cases in the target

## Rate Limiting

TestRail API may return HTTP 429. Respect the `Retry-After` header. Implement retry logic with 3 attempts.

## Recommended Script Language

Use **Python** for the copy script — it handles JSON, regex, and HTTP natively. Avoid complex bash scripts with jq/python subprocess chains.

## Pagination

TestRail returns max 250 items per request. Check `_links.next` to detect more pages and increment `offset` by 250.
