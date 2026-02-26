#!/usr/bin/env python3
"""Copy Freemium SDK test cases into Bills API with BCR/SALT -> Partner renaming."""

import copy
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

# Section mapping: (old_id, new_id)
# ALL sections get BCR/SALT -> Partner text replacement in case content
SECTIONS = [
    (260, 685),   # Main structure
    (265, 688),   # Default state
    (266, 689),   # Activate trial
    (267, 690),   # Active state
    (541, 691),   # Cancel / renew subscription
    (314, 692),   # Activate paid subscription
    (557, 698),   # SALT -> Partner
    (312, 693),   # Upgrade/downgrade trial subscription
    (540, 694),   # Upgrade/downgrade paid subscription
    (558, 695),   # SALT - Biometrics -> Partner - Biometrics
    (555, 699),   # 2 months campaign - Pago/BCR -> Pago/Partner
    (556, 700),   # Gratuity campaign - Salt -> Partner
    (542, 697),   # Payment limits
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


def replace_text(text):
    """Replace BCR, SALT, George app in text, protecting URLs inside href attributes."""
    if not text or not isinstance(text, str):
        return text
    hrefs = []
    def save_href(m):
        hrefs.append(m.group(0))
        return f'__HREF_{len(hrefs)-1}__'
    text = re.sub(r'href="[^"]*"', save_href, text)

    # Replacements
    text = text.replace('George app', 'Partner app')
    text = text.replace('George App', 'Partner app')
    text = re.sub(r'\bBCR\b', 'Partner', text)
    text = re.sub(r'\bSALT\b', 'Partner', text)
    text = re.sub(r'\bSalt\b', 'Partner', text)

    # Restore hrefs
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


def copy_case(case, new_section_id):
    """Copy a case with BCR/SALT->Partner replacement. Raw API = flat custom fields."""
    title = replace_text(case["title"])
    preconds = replace_text(case.get("custom_preconds") or "")
    expected = replace_text(case.get("custom_expected") or "")
    steps_sep = case.get("custom_steps_separated")
    bdd = case.get("custom_testrail_bdd_scenario")
    mission = case.get("custom_mission")
    goals = case.get("custom_goals")
    auto_type = case.get("custom_automation_type", 0)

    if steps_sep:
        steps_sep = copy.deepcopy(steps_sep)
        for step in steps_sep:
            step["content"] = replace_text(step.get("content", ""))
            step["expected"] = replace_text(step.get("expected", ""))

    payload = {
        "title": title,
        "custom_automation_type": auto_type or 0,
    }

    if steps_sep:
        payload["template_id"] = 2
        payload["custom_steps_separated"] = [
            {"content": s.get("content", ""), "expected": s.get("expected", "")}
            for s in steps_sep
        ]
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
        payload["custom_testrail_bdd_scenario"] = replace_text(bdd)
    if mission:
        payload["custom_mission"] = replace_text(mission)
    if goals:
        payload["custom_goals"] = replace_text(goals)

    return api_request("POST", f"add_case/{new_section_id}", payload)


def main():
    total_copied = 0
    total_errors = 0

    for old_id, new_id in SECTIONS:
        print(f"=== Section {old_id} -> {new_id} ===")
        try:
            cases = get_cases(old_id)
        except Exception as e:
            print(f"  ERROR fetching: {e}")
            total_errors += 1
            continue

        if not cases:
            print(f"  No cases (container section)")
            continue

        print(f"  Found {len(cases)} cases")
        for case in cases:
            try:
                result = copy_case(case, new_id)
                print(f"  {case['id']} -> {result.get('id','?')}: {case['title'][:60]}")
                total_copied += 1
            except Exception as e:
                print(f"  ERROR copying case {case['id']}: {e}")
                total_errors += 1

    print(f"\n{'='*40}")
    print(f"DONE! Copied: {total_copied}, Errors: {total_errors}")
    print(f"{'='*40}")

if __name__ == "__main__":
    main()
