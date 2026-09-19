#!/usr/bin/env bash
# Generate a descriptive sync commit message from the ACTUAL diff between
# the mirror's previous HEAD and the fresh export. Names new/changed leaves
# with their family/topic so public history reads like a changelog, not
# "sync: N skills" (founder 2026-09-03: commits should highlight the new
# leaves and topics covered).
#
# Usage: gen_sync_commit_msg.sh <MIRROR_DIR>
# Prints the commit message (subject + body) to stdout.

set -euo pipefail
MIRROR="${1:?mirror dir required}"

cd "$MIRROR"

LEAVES=$(python3 -c "import json; print(json.load(open('docs/metrics.json'))['leaves'])")
PACKS=$(python3 -c "import json; print(json.load(open('docs/metrics.json'))['live_packs'])")
FAMILIES=$(python3 -c "import json; print(json.load(open('docs/metrics.json'))['families'])")

# ---- what changed vs the previous public HEAD ----
# Files are STAGED (git add -A ran before this script) — diff --cached.
# New leaf dirs: skills/<family>/<pack>/<leaf>/SKILL.md that are new/added.
DIFF_BASE="git diff --cached HEAD"
# `awk NR<=N` and NOT `head -N`: head closes the pipe at N lines, which
# SIGPIPEs the producer, and under `set -o pipefail` that kills this script
# (exit 141). Harmless while a sync added tens of leaves; fatal the first
# time one added hundreds. awk reads to EOF, so the producer always
# finishes. Same truncation, no signal.
# The FULL sets, for counting. Truncating then counting reports the cap
# instead of the change: a 672-leaf sync committed as "add 40 leaf
# skill(s)" is a permanent, wrong public record of what happened.
NEW_LEAF_ALL=$($DIFF_BASE --name-status -- 'skills/*/*/*/SKILL.md' | awk '$1=="A" {print $2}')
NEW_LEAF_COUNT=$(printf '%s' "$NEW_LEAF_ALL" | grep -c 'SKILL\.md' || true)
NEW_FAMS_ALL=$(printf '%s\n' "$NEW_LEAF_ALL" | cut -d/ -f2 | sort -u | tr '\n' ',' | sed 's/,$//')

# And the capped set, for the list a human reads.
NEW_LEAF_FILES=$(printf '%s\n' "$NEW_LEAF_ALL" | awk 'NR<=40')
MOD_LEAF_FILES=$($DIFF_BASE --name-status -- 'skills/*/*/*/SKILL.md' | awk '$1=="M" {print $2}' | awk 'NR<=20')
NEW_PACK_DIRS=$($DIFF_BASE --name-status -- 'skills/*/*/*/SKILL.md' | awk '$1=="A" {print $2}' | sed -E 's|skills/([^/]+)/([^/]+)/.*|\1/\2|' | sort -u | awk 'NR<=20')

# Extract leaf names + families for the body
declare -a LEAF_LINES=()
if [ -n "$NEW_LEAF_FILES" ]; then
  while IFS= read -r f; do
    fam=$(echo "$f" | cut -d/ -f2)
    pack=$(echo "$f" | cut -d/ -f3)
    leaf=$(echo "$f" | cut -d/ -f4)
    LEAF_LINES+=("  - ${fam}/${pack}: ${leaf}")
  done <<< "$NEW_LEAF_FILES"
fi

# Subject: highlight the dominant change
if [ -n "$NEW_LEAF_FILES" ]; then
  NEW_COUNT="$NEW_LEAF_COUNT"
  NEW_FAMS="$NEW_FAMS_ALL"
  SUBJECT="add ${NEW_COUNT} leaf skill(s) across ${NEW_FAMS} — ${LEAVES} total"
elif [ -n "$MOD_LEAF_FILES" ]; then
  SUBJECT="update leaf skill content — ${LEAVES} skills, ${PACKS} packs"
else
  SUBJECT="sync repo state — ${LEAVES} skills, ${PACKS} packs, ${FAMILIES} families"
fi

# Body
BODY="Automated sync from the private dev tree (ops/automation/publish-public.sh).
Gates verified inside this export: validate, attest, visuals-check, package-test.

Stats: ${LEAVES} leaves · ${PACKS} packs · ${FAMILIES} families"

if [ "${#LEAF_LINES[@]}" -gt 0 ]; then
  BODY+="

New leaves in this sync:
$(printf '%s\n' "${LEAF_LINES[@]}")"
  if [ "${NEW_LEAF_COUNT:-0}" -gt "${#LEAF_LINES[@]}" ]; then
    # A truncated list that does not say it is truncated reads as complete.
    BODY+="
  ... and $(( NEW_LEAF_COUNT - ${#LEAF_LINES[@]} )) more not listed here"
  fi
fi

if [ -n "$NEW_PACK_DIRS" ] && [ "$NEW_COUNT" -gt 0 ]; then
  BODY+="

Packs touched: $(echo "$NEW_PACK_DIRS" | tr '\n' ' ')"
fi

printf '%s\n\n%s\n' "$SUBJECT" "$BODY"
