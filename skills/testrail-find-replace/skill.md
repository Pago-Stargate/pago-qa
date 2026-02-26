---
name: testrail-find-replace
description: Bulk find and replace text across TestRail test cases in a section or entire suite. Supports regex, href URL protection, and dry-run preview.
---

# TestRail Find & Replace Skill

Perform bulk text find & replace across test cases in TestRail sections.

## What You Need From the User

Ask the user for:
1. **Scope** — section ID(s) to search in, or "entire suite" for all sections under a parent
2. **Project ID and Suite ID**
3. **Find/replace pairs** — what text to find and what to replace it with
4. **Options**:
   - Protect URLs in `href` attributes? (default: yes)
   - Case-sensitive? (default: yes)
   - Regex or literal? (default: literal)
5. **Credentials** — TestRail URL and API credentials

## Execution Steps

### Step 1: Scan (Dry Run)

Before making any changes, scan all cases and report findings:

1. Get all sections under the target parent using `get_sections(project_id, suite_id)`
2. For each section, fetch cases via the raw API (flat custom fields at top level):

```
GET /api/v2/get_cases/<project_id>&suite_id=<suite_id>&section_id=<section_id>&limit=250
```

3. Check these fields in each case for matches:
   - `title`
   - `custom_preconds`
   - `custom_expected`
   - `custom_steps_separated[].content`
   - `custom_steps_separated[].expected`
   - `refs`

4. Present findings to the user:
```
Found 14 occurrences across 10 cases:
  Case 4656 [title]: "Succes" → "Success"
  Case 4657 [step[1].content]: "do to" → "due to"
  ...
```

Wait for user confirmation before proceeding.

### Step 2: Apply Changes

For each case with matches:

1. Fetch the full case via `GET /api/v2/get_case/<case_id>`
2. Apply replacements to all text fields
3. **Protect href URLs** if enabled:
   ```python
   # Save hrefs
   hrefs = []
   def save_href(m):
       hrefs.append(m.group(0))
       return f'__HREF_{len(hrefs)-1}__'
   text = re.sub(r'href="[^"]*"', save_href, text)

   # Apply replacements
   text = text.replace(old, new)

   # Restore hrefs
   for i, href in enumerate(hrefs):
       text = text.replace(f'__HREF_{i}__', href)
   ```
4. Update via `POST /api/v2/update_case/<case_id>` with only the changed fields

### Step 3: Verify

Re-scan all cases to confirm zero remaining matches. Report results.

## Important API Notes

- **Raw API returns flat custom fields**: `case["custom_preconds"]`, NOT `case["custom"]["custom_preconds"]`
- **MCP update_case tool** works for simple updates but may not handle `custom_steps_separated` arrays. Use `curl` or `urllib` for step updates.
- **Updating steps**: When updating `custom_steps_separated`, send the full array with only `content` and `expected` keys per step. Extra keys like `additional_info` and `refs` are auto-populated.
- **Pagination**: Max 250 cases per request. Check `_links.next`.

## Common Use Cases

- Renaming a brand/product across test cases (e.g., "BCR" → "Partner")
- Fixing consistent typos across a suite
- Updating environment names or URLs
- Removing references to deprecated features
