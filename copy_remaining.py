#!/usr/bin/env python3
"""Copy remaining sections: BCR->Partner (546->667) and Happy Flow Quick Scan (560->668)."""

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

SECTIONS = [
    (546, 667, True),   # BCR -> Partner
    (560, 668, False),  # Happy Flow Quick Scan
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
    custom = case.get("custom", {})
    title = case["title"]
    preconds = custom.get("custom_preconds") or ""
    expected = custom.get("custom_expected") or ""
    steps_sep = custom.get("custom_steps_separated")
    bdd = custom.get("custom_testrail_bdd_scenario")
    mission = custom.get("custom_mission")
    goals = custom.get("custom_goals")
    auto_type = custom.get("custom_automation_type", 0)

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
        cases = get_cases(old_id)
        if not cases:
            print(f"  No cases")
            continue
        print(f"  Found {len(cases)} cases")
        for case in cases:
            try:
                result = copy_case(case, new_id, is_bcr)
                new_case_id = result.get("id", "?")
                print(f"  {case['id']} -> {new_case_id}: {case['title'][:70]}")
                total_copied += 1
            except Exception as e:
                print(f"  ERROR copying case {case['id']}: {e}")
                total_errors += 1

    print(f"\n{'='*40}")
    print(f"DONE! Copied: {total_copied}, Errors: {total_errors}")
    print(f"{'='*40}")

if __name__ == "__main__":
    main()
