#!/usr/bin/env bash
# Sync the GitHub About sidebar (description · homepage · topics) from
# docs/metrics.json, so the public numbers come from the tree at HEAD and can
# never be hand-edited into staleness. Needs network plus a repo-scoped token
# (read from the origin remote URL at runtime — never stored here), so it is
# deliberately NOT part of the offline gate battery. Run after counts change:
#   make about
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

url=$(git remote get-url origin)
token=$(printf '%s' "$url" | sed -E 's#https://[^:]+:([^@]+)@.*#\1#')
slug=$(printf '%s' "$url" | sed -E -e 's#.*github\.com/##' -e 's#\.git$##')
if [ "$token" = "$url" ] || [ "$slug" = "$url" ]; then
  echo "FAIL about: origin remote has no embedded token or unexpected shape" >&2
  exit 1
fi

payload=$(/usr/bin/python3 - <<'PY'
import json
m = json.load(open("docs/metrics.json"))
desc = ("\U0001F680 The aerospace knowledge layer for AI agents — "
        f"{m['leaves']} verified skills in {m['live_packs']} installable packs "
        f"across {m['families']} engineering families, mapped to "
        f"{m['standards']} standards (ECSS · DO-178C · NASA) and "
        f"proven by a {m['corpus_tasks']}-task deterministic gate battery. "
        "AgentSkills.io format · Apache-2.0 · by Ashforde OÜ")
print(json.dumps({"description": desc, "homepage": "https://ashforde.org"}))
PY
)

topics='{"names":["aerospace","aerospace-engineering","ai-agents","agent-skills","llm","claude-code","skills-library","avionics","do-178c","ecss","arp4754a","systems-engineering","gnc","propulsion","aerodynamics","space-systems","flight-test","standards-compliance"]}'

resp=$(mktemp)
trap 'rm -f "$resp"' EXIT

code=$(curl -sS -o "$resp" -w '%{http_code}' -X PATCH \
  -H "Authorization: Bearer $token" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$slug" -d "$payload")
if [ "$code" != "200" ]; then
  echo "FAIL about: description/homepage PATCH -> HTTP $code" >&2
  cat "$resp" >&2
  exit 1
fi

code=$(curl -sS -o "$resp" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $token" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$slug/topics" -d "$topics")
if [ "$code" != "200" ]; then
  echo "FAIL about: topics PUT -> HTTP $code" >&2
  cat "$resp" >&2
  exit 1
fi

n=$(/usr/bin/python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['names']))" "$resp")
echo "PASS about: $slug description + homepage synced from docs/metrics.json, $n topics set"
