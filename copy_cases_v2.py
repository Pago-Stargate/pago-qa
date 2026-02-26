#!/usr/bin/env python3
"""Copy test cases from Bills SDK to Bills API in TestRail - v2 (flat custom fields)."""

import json
import os
import re
import time
import urllib.request
import urllib.error
import base64

AUTH = os.environ.get("TESTRAIL_AUTH", "user@example.com:api_key")
BASE = "https://pago.testrail.io/index.php?/api/v2"
AUTH_HEADER = "Basic " + base64.b64encode(AUTH.encode()).decode()

# Section mapping: (old_id, new_id, is_bcr)
# Excludes SALT (547) and non-existent section 165
SECTIONS = [
    (123, 636, False),
    (124, 647, False),
    (125, 648, False),
    (251, 649, False),
    (126, 650, False),
    (128, 651, False),
    (129, 652, False),
    (253, 653, False),
    (131, 669, False),
    (134, 670, False),
    (135, 671, False),
    (138, 681, False),
    (139, 682, False),
    (140, 683, False),
    (254, 655, False),
    (142, 673, False),
    (136, 674, False),
    (144, 675, False),
    (145, 676, False),
    (146, 677, False),
    (147, 678, False),
    (149, 657, False),
    (150, 658, False),
    (152, 659, False),
    (178, 679, False),
    (153, 639, False),
    (256, 640, False),
    (154, 660, False),
    (258, 661, False),
    (259, 662, False),
    (157, 663, False),
    (161, 664, False),
    (164, 680, False),
    (162, 665, False),
    (163, 666, False),
    (122, 642, False),
    (257, 643, False),
    (546, 667, True),   # BCR -> Partner
    (560, 668, False),
]


def api_request(method, path, data=None):
    url = f"{BASE}/{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", AUTH_HEADER)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                print(f"    Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            print(f"    HTTP {e.code}: {error_body}")
            raise
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise


def replace_bcr_text(text):
    """Replace BCR/George app in text, protecting URLs inside href attributes."""
    if not text or not isinstance(text, str):
        return text
    hrefs = []
    def save_href(m):
        hrefs.append(m.group(0))
        return f'__HREF_{len(hrefs)-1}__'
    text = re.sub(r'href="[^"]*"', save_href, text)
    text = text.replace('George app', 'Partner app')
    text = text.replace('George App', 'Partner app')
    text = re.sub(r'\bBCR\b', 'Partner', text)
    for i, href in enumerate(hrefs):
        text = text.replace(f'__HREF_{i}__', href)
    return text


def get_cases(section_id):
    """Fetch all cases from a section with pagination."""
    cases = []
    offset = 0
    while True:
        resp = api_request("GET", f"get_cases/5&suite_id=5&section_id={section_id}&limit=250&offset={offset}")
        batch = resp.get("cases", [])
        cases.extend(batch)
        if not resp.get("_links", {}).get("next"):
            break
        offset += 250
    return cases


def copy_case(case, new_section_id, is_bcr):
    """Copy a single case to a new section. Raw API returns flat custom fields."""
    # Raw API: custom fields are at TOP LEVEL (e.g. case["custom_preconds"])
    title = case["title"]
    preconds = case.get("custom_preconds") or ""
    expected = case.get("custom_expected") or ""
    steps_sep = case.get("custom_steps_separated")
    bdd = case.get("custom_testrail_bdd_scenario")
    mission = case.get("custom_mission")
    goals = case.get("custom_goals")
    auto_type = case.get("custom_automation_type", 0)

    # Deep copy steps to avoid mutating source
    if steps_sep:
        import copy
        steps_sep = copy.deepcopy(steps_sep)

    # Apply BCR -> Partner replacements
    if is_bcr:
        title = replace_bcr_text(title)
        preconds = replace_bcr_text(preconds)
        expected = replace_bcr_text(expected)
        if steps_sep:
            for step in steps_sep:
                step["content"] = replace_bcr_text(step.get("content", ""))
                step["expected"] = replace_bcr_text(step.get("expected", ""))

    payload = {
        "title": title,
        "custom_automation_type": auto_type or 0,
    }

    # Use template_id=2 (Steps) when steps exist, else template_id=1 (Text)
    if steps_sep:
        payload["template_id"] = 2
        clean_steps = [{"content": s.get("content", ""), "expected": s.get("expected", "")} for s in steps_sep]
        payload["custom_steps_separated"] = clean_steps
    else:
        payload["template_id"] = 1
        payload["custom_expected"] = expected or "N/A"

    if preconds:
        payload["custom_preconds"] = preconds
    if case.get("type_id"):
        payload["type_id"] = case["type_id"]
    if case.get("priority_id"):
        payload["priority_id"] = case["priority_id"]
    if case.get("refs"):
        payload["refs"] = case["refs"]
    if bdd:
        payload["custom_testrail_bdd_scenario"] = bdd
    if mission:
        payload["custom_mission"] = mission
    if goals:
        payload["custom_goals"] = goals

    return api_request("POST", f"add_case/{new_section_id}", payload)


def main():
    total_copied = 0
    total_errors = 0

    for old_id, new_id, is_bcr in SECTIONS:
        label = " [BCR->Partner]" if is_bcr else ""
        print(f"=== Section {old_id} -> {new_id}{label} ===")

        try:
            cases = get_cases(old_id)
        except Exception as e:
            print(f"  ERROR fetching cases: {e}")
            total_errors += 1
            continue

        if not cases:
            print(f"  No cases in section {old_id}")
            continue

        print(f"  Found {len(cases)} cases")

        for case in cases:
            try:
                result = copy_case(case, new_id, is_bcr)
                new_case_id = result.get("id", "?")
                print(f"  {case['id']} -> {new_case_id}: {case['title'][:60]}")
                total_copied += 1
            except Exception as e:
                print(f"  ERROR copying case {case['id']}: {e}")
                total_errors += 1

    print(f"\n{'='*40}")
    print(f"DONE! Copied: {total_copied}, Errors: {total_errors}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
