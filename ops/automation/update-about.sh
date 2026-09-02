#!/usr/bin/env bash
# Sync the GitHub About sidebar (description · homepage · topics) from
# docs/metrics.json, so the public numbers come from the tree and can never be
# hand-edited into staleness. Needs network plus a repo-scoped token (read from
# the origin remote URL at runtime — never stored here), so it is deliberately
# NOT one of the offline gates. Three ways it runs:
#   make about                    — manual, from the local tree
#   .ci-native --best-effort line — every push refreshes About (non-fatal:
#                                   a network flake must never block a push)
#   launchd org.ashforde.aeroskills-about (machine-local, every 6h)
#                                 — --from-origin trues About up to whatever
#                                   is actually on origin/main, catching pushes
#                                   from clones without the hook
set -euo pipefail

# --best-effort: run normally but never exit nonzero (gate-safe wrapper)
if [[ " $* " == *" --best-effort "* ]]; then
  args=()
  for a in "$@"; do [[ "$a" == --best-effort ]] || args+=("$a"); done
  if ! bash "$0" ${args[@]+"${args[@]}"}; then
    echo "WARN about: sync failed (non-fatal — network or token unavailable)"
  fi
  exit 0
fi

cd "$(git rev-parse --show-toplevel)"

url=$(git remote get-url origin)
token=$(printf '%s' "$url" | sed -E 's#https://[^:]+:([^@]+)@.*#\1#')
slug=$(printf '%s' "$url" | sed -E -e 's#.*github\.com/##' -e 's#\.git$##')
if [ "$token" = "$url" ] || [ "$slug" = "$url" ]; then
  echo "FAIL about: origin remote has no embedded token or unexpected shape" >&2
  exit 1
fi

# --from-origin: sync from what is actually published on origin/main, not the
# local tree (the launchd drift-guard uses this; a dirty checkout is ignored)
metrics="docs/metrics.json"
src="local tree"
if [[ " $* " == *" --from-origin "* ]]; then
  git fetch -q origin main
  metrics=$(mktemp)
  git show origin/main:docs/metrics.json > "$metrics"
  src="origin/main"
fi

payload=$(METRICS="$metrics" /usr/bin/python3 - <<'PY'
import json, os
m = json.load(open(os.environ["METRICS"]))
desc = ("\U0001F680 The aerospace knowledge layer for AI agents — "
        f"{m['leaves']} verified skills in {m['live_packs']} installable packs "
        f"across {m['families']} engineering families, mapped to "
        f"{m['standards']} standards (ECSS · DO-178C · NASA) and "
        f"proven by a {m['corpus_tasks']}-task deterministic gate battery. "
        "AgentSkills.io format · Apache-2.0 · by Ashforde OÜ")
print(json.dumps({"description": desc, "homepage": "https://ashforde.org"}))
PY
)

topics='{"names":["aerospace","aerospace-engineering","ai-agents","agent-skills","llm","claude-code","skills-library","avionics","do-178c","ecss","arp4754a","systems-engineering","gnc","propulsion","aerodynamics","space-systems","flight-test","standards-compliance","mcp"]}'

resp=$(mktemp)
trap 'rm -f "$resp"' EXIT

code=$(curl -sS --max-time 20 -o "$resp" -w '%{http_code}' -X PATCH \
  -H "Authorization: Bearer $token" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$slug" -d "$payload")
if [ "$code" != "200" ]; then
  echo "FAIL about: description/homepage PATCH -> HTTP $code" >&2
  cat "$resp" >&2
  exit 1
fi

code=$(curl -sS --max-time 20 -o "$resp" -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $token" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$slug/topics" -d "$topics")
if [ "$code" != "200" ]; then
  echo "FAIL about: topics PUT -> HTTP $code" >&2
  cat "$resp" >&2
  exit 1
fi

n=$(/usr/bin/python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['names']))" "$resp")
echo "PASS about: $slug description + homepage synced from $src, $n topics set"
