---
name: testrail-audit
description: Audit TestRail test cases for quality issues — typos, grammar errors, broken links, missing fields, and inconsistencies. Use for QA hygiene checks.
---

# TestRail Audit Skill

Scan test cases for typos, grammar errors, broken/internal links, missing content, and naming inconsistencies.

## What You Need From the User

Ask the user for:
1. **Scope** — section ID(s) or "entire project/suite"
2. **Project ID and Suite ID**
3. **What to check** (default: all):
   - Typos and misspellings
   - Grammar (verb tenses, word order)
   - Broken or internal-only links (Jira, Confluence)
   - Missing required content (empty preconditions, no steps)
   - Naming inconsistencies (e.g., mixed use of "BCR" and "Partner")
4. **Credentials** — TestRail URL and API credentials

## Audit Checks

### 1. Typos & Misspellings

Scan all text fields using regex patterns for common errors:

```python
TYPO_PATTERNS = [
    (r'\bpayed\b', 'paid'),
    (r'\bfounded\b', 'found'),         # "bills are founded" → "found"
    (r'\brefference\b', 'reference'),
    (r'\bSucces\b', 'Success'),
    (r'\brecieved\b', 'received'),
    (r'\bpermision\b', 'permission'),
    (r'\bsubscritpion\b', 'subscription'),
    (r'\bdesing\b', 'design'),
    (r'\bdefualt\b', 'default'),
    (r'\bavailble\b', 'available'),
    (r'\binsuficient\b', 'insufficient'),
    (r'\bthe the\b', 'the'),           # duplicate words
    (r'\bis is\b', 'is'),
    # Add project-specific terms as needed
]
```

### 2. Grammar Issues

```python
GRAMMAR_PATTERNS = [
    (r'\bdo to\b', 'due to'),
    (r'\bpreviously data entered\b', 'previously entered data'),
    (r'\bits displayed\b', None),       # check: should it be "it's displayed"?
    (r'\bfinalised\b', 'finalized'),    # if project uses American English
]
```

### 3. Link Audit

Find all `<a href="...">` tags and check for:
- **Internal links** (Jira, Confluence, internal wikis) that shouldn't be in shared test cases
- **Broken URL patterns** (malformed hrefs)

```python
INTERNAL_LINK_PATTERNS = [
    r'pagojira\.atlassian\.net',
    r'confluence\.',
    r'jira\.',
    r'\.atlassian\.net',
    r'internal\.',
    r'intranet\.',
]
```

### 4. Missing Content

Flag cases with potential issues:
- Empty `custom_preconds` (no preconditions defined)
- Template mismatch: `template_id=2` but `custom_steps_separated` is null
- Cases with title only and no other content

### 5. Naming Consistency

Check for terms that should have been migrated/renamed:
- Collect all unique terms and flag inconsistencies (e.g., some cases say "BCR", others say "Partner")
- User provides a list of old → new term pairs to verify

## Execution

### Step 1: Collect All Cases

Fetch all sections under the target parent, then all cases from each section via the raw API:

```
GET /api/v2/get_cases/<project_id>&suite_id=<suite_id>&section_id=<id>&limit=250
```

**Remember**: Raw API returns flat custom fields (`case["custom_preconds"]`, not nested).

### Step 2: Run Checks

For each case, strip HTML tags before pattern matching:
```python
import re
def strip_html(text):
    return re.sub(r'<[^>]+>', ' ', text) if text else ''
```

Fields to check: `title`, `custom_preconds`, `custom_expected`, `custom_steps_separated[].content`, `custom_steps_separated[].expected`, `refs`.

### Step 3: Report

Present findings grouped by category:

```
=== Typos (8 issues) ===
  Case 4387 [title]: "founded" → "found"
  Case 4600 [expected]: "refference" → "reference"
  ...

=== Grammar (3 issues) ===
  Case 4657 [step content]: "do to" → "due to"
  ...

=== Internal Links (4 cases) ===
  Case 4651 [preconds]: Confluence link found
  ...

=== Summary ===
  Scanned: 502 cases
  Issues found: 15
  Cases affected: 12
```

### Step 4: Fix (With Confirmation)

After presenting the report, ask the user which categories to auto-fix. Apply fixes using `POST /api/v2/update_case/<case_id>`.

Always re-scan after fixing to confirm zero remaining issues.

## Tips

- Run this skill periodically (e.g., after each migration or sprint) to maintain test case quality
- Keep a project-specific typo list and add to it as new patterns emerge
- For large suites (500+ cases), the scan takes 1-2 minutes due to API pagination
