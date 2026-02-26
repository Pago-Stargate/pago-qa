#!/bin/bash
# Copy test cases from Bills SDK to Bills API
# Section mapping: old_id -> new_id
# Excludes: SALT (547), sections with 0 direct cases (119, 120, 130, 137, 141, 148, 121, 167, 559)

AUTH="${TESTRAIL_AUTH:-user@example.com:api_key}"
BASE="https://pago.testrail.io/index.php?/api/v2"

# Sections with cases to copy (old_id:new_id:is_bcr)
# is_bcr=1 means apply BCR->Partner replacement
SECTIONS=(
  "123:636:0"
  "124:647:0"
  "125:648:0"
  "251:649:0"
  "126:650:0"
  "128:651:0"
  "129:652:0"
  "253:653:0"
  "131:669:0"
  "134:670:0"
  "135:671:0"
  "138:681:0"
  "139:682:0"
  "140:683:0"
  "254:655:0"
  "142:673:0"
  "136:674:0"
  "144:675:0"
  "145:676:0"
  "146:677:0"
  "147:678:0"
  "149:657:0"
  "150:658:0"
  "152:659:0"
  "178:679:0"
  "153:639:0"
  "256:640:0"
  "154:660:0"
  "258:661:0"
  "259:662:0"
  "157:663:0"
  "161:664:0"
  "164:680:0"
  "162:665:0"
  "163:666:0"
  "122:642:0"
  "257:643:0"
  "165:644:0"
  "546:667:1"
  "560:668:0"
)

TOTAL_COPIED=0
TOTAL_ERRORS=0

replace_bcr() {
  # Replace BCR/George app in text fields, but protect URLs inside href=""
  local text="$1"
  if [ -z "$text" ] || [ "$text" = "null" ]; then
    echo "$text"
    return
  fi
  # Use Python for reliable regex replacement
  python3 -c "
import re, sys, json

text = sys.stdin.read()

# Protect href URLs by replacing them with placeholders
hrefs = []
def save_href(m):
    hrefs.append(m.group(0))
    return f'__HREF_PLACEHOLDER_{len(hrefs)-1}__'

text = re.sub(r'href=\"[^\"]*\"', save_href, text)

# Replace George app -> Partner app (case sensitive)
text = text.replace('George app', 'Partner app')
text = text.replace('George App', 'Partner app')

# Replace standalone BCR -> Partner
# BCR followed by word boundary, not inside a URL
text = re.sub(r'\bBCR\b', 'Partner', text)

# Restore href URLs
for i, href in enumerate(hrefs):
    text = text.replace(f'__HREF_PLACEHOLDER_{i}__', href)

sys.stdout.write(text)
" <<< "$text"
}

process_steps_separated() {
  local steps_json="$1"
  local is_bcr="$2"

  if [ -z "$steps_json" ] || [ "$steps_json" = "null" ]; then
    echo "null"
    return
  fi

  if [ "$is_bcr" = "0" ]; then
    echo "$steps_json"
    return
  fi

  # Use Python to process steps
  python3 -c "
import re, sys, json

steps = json.loads(sys.stdin.read())
hrefs_global = []

def protect_and_replace(text):
    if not text or not isinstance(text, str):
        return text
    hrefs = []
    def save_href(m):
        hrefs.append(m.group(0))
        return f'__HREF_PLACEHOLDER_{len(hrefs)-1}__'
    text = re.sub(r'href=\"[^\"]*\"', save_href, text)
    text = text.replace('George app', 'Partner app')
    text = text.replace('George App', 'Partner app')
    text = re.sub(r'\bBCR\b', 'Partner', text)
    for i, href in enumerate(hrefs):
        text = text.replace(f'__HREF_PLACEHOLDER_{i}__', href)
    return text

for step in steps:
    if 'content' in step:
        step['content'] = protect_and_replace(step.get('content', ''))
    if 'expected' in step:
        step['expected'] = protect_and_replace(step.get('expected', ''))

print(json.dumps(steps))
" <<< "$steps_json"
}

for mapping in "${SECTIONS[@]}"; do
  IFS=':' read -r old_id new_id is_bcr <<< "$mapping"

  echo "=== Processing section $old_id -> $new_id (BCR replace: $is_bcr) ==="

  # Fetch all cases from old section (paginate)
  offset=0
  while true; do
    response=$(curl -s "$BASE/get_cases/5&suite_id=5&section_id=$old_id&limit=250&offset=$offset" \
      -u "$AUTH")

    cases=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('cases',[])))")
    count=$(echo "$cases" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

    if [ "$count" = "0" ]; then
      echo "  No (more) cases in section $old_id"
      break
    fi

    echo "  Found $count cases (offset $offset)"

    # Process each case
    for i in $(seq 0 $((count - 1))); do
      case_data=$(echo "$cases" | python3 -c "
import sys, json
cases = json.load(sys.stdin)
c = cases[$i]
print(json.dumps(c))
")

      title=$(echo "$case_data" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['title']))")
      type_id=$(echo "$case_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type_id',''))")
      priority_id=$(echo "$case_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('priority_id',''))")
      refs=$(echo "$case_data" | python3 -c "import sys,json; r=json.load(sys.stdin).get('refs'); print(json.dumps(r) if r else 'null')")

      # Extract custom fields
      custom_automation_type=$(echo "$case_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('custom',{}).get('custom_automation_type',0))")
      custom_preconds=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_preconds'); print(json.dumps(v) if v else 'null')")
      custom_expected=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_expected'); print(json.dumps(v) if v else 'null')")
      custom_steps_separated=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_steps_separated'); print(json.dumps(v) if v else 'null')")
      custom_bdd=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_testrail_bdd_scenario'); print(json.dumps(v) if v else 'null')")
      custom_mission=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_mission'); print(json.dumps(v) if v else 'null')")
      custom_goals=$(echo "$case_data" | python3 -c "import sys,json; v=json.load(sys.stdin).get('custom',{}).get('custom_goals'); print(json.dumps(v) if v else 'null')")

      # Apply BCR->Partner replacement if needed
      if [ "$is_bcr" = "1" ]; then
        title_raw=$(echo "$case_data" | python3 -c "import sys,json; print(json.load(sys.stdin)['title'])")
        title_replaced=$(replace_bcr "$title_raw")
        title=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$title_replaced")

        if [ "$custom_preconds" != "null" ]; then
          preconds_raw=$(echo "$custom_preconds" | python3 -c "import sys,json; print(json.load(sys.stdin))")
          preconds_replaced=$(replace_bcr "$preconds_raw")
          custom_preconds=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$preconds_replaced")
        fi

        if [ "$custom_expected" != "null" ]; then
          expected_raw=$(echo "$custom_expected" | python3 -c "import sys,json; print(json.load(sys.stdin))")
          expected_replaced=$(replace_bcr "$expected_raw")
          custom_expected=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$expected_replaced")
        fi

        custom_steps_separated=$(process_steps_separated "$custom_steps_separated" "$is_bcr")
      fi

      # Build the JSON payload using Python for safety
      payload=$(python3 -c "
import json, sys

new_section = int(sys.argv[1])
title = json.loads(sys.argv[2])
type_id = int(sys.argv[3]) if sys.argv[3] else None
priority_id = int(sys.argv[4]) if sys.argv[4] else None
refs = json.loads(sys.argv[5]) if sys.argv[5] != 'null' else None
auto_type = int(sys.argv[6]) if sys.argv[6] else 0
preconds = json.loads(sys.argv[7]) if sys.argv[7] != 'null' else None
expected = json.loads(sys.argv[8]) if sys.argv[8] != 'null' else None
steps_sep = json.loads(sys.argv[9]) if sys.argv[9] != 'null' else None
bdd = json.loads(sys.argv[10]) if sys.argv[10] != 'null' else None
mission = json.loads(sys.argv[11]) if sys.argv[11] != 'null' else None
goals = json.loads(sys.argv[12]) if sys.argv[12] != 'null' else None

payload = {
    'title': title,
    'section_id': new_section,
    'custom_automation_type': auto_type,
}

if type_id:
    payload['type_id'] = type_id
if priority_id:
    payload['priority_id'] = priority_id
if refs:
    payload['refs'] = refs
if preconds:
    payload['custom_preconds'] = preconds
if expected:
    payload['custom_expected'] = expected
if steps_sep:
    # Clean steps: only keep content and expected
    clean_steps = []
    for s in steps_sep:
        clean = {'content': s.get('content',''), 'expected': s.get('expected','')}
        clean_steps.append(clean)
    payload['custom_steps_separated'] = clean_steps
if bdd:
    payload['custom_testrail_bdd_scenario'] = bdd
if mission:
    payload['custom_mission'] = mission
if goals:
    payload['custom_goals'] = goals

print(json.dumps(payload))
" "$new_id" "$title" "$type_id" "$priority_id" "$refs" "$custom_automation_type" "$custom_preconds" "$custom_expected" "$custom_steps_separated" "$custom_bdd" "$custom_mission" "$custom_goals")

      # Create the case
      result=$(curl -s -X POST "$BASE/add_case/$new_id" \
        -H "Content-Type: application/json" \
        -u "$AUTH" \
        -d "$payload")

      new_case_id=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id','ERROR'))" 2>/dev/null)

      if [ "$new_case_id" = "ERROR" ] || [ -z "$new_case_id" ]; then
        echo "  ERROR creating case: $result"
        TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
      else
        old_case_id=$(echo "$case_data" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        echo "  Copied case $old_case_id -> $new_case_id"
        TOTAL_COPIED=$((TOTAL_COPIED + 1))
      fi
    done

    # Check for more pages
    has_next=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('_links',{}).get('next') else 'no')")
    if [ "$has_next" = "no" ]; then
      break
    fi
    offset=$((offset + 250))
  done
done

echo ""
echo "=============================="
echo "DONE! Copied: $TOTAL_COPIED cases, Errors: $TOTAL_ERRORS"
echo "=============================="
