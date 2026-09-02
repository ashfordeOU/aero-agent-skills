#!/usr/bin/env bash
# Sync the dev tree (arjun-0077, private TEST environment) to the public
# release repo (github.com/ashfordeOU/aero-agent-skills). Founder
# 2026-09-02: "arjun repo stays for testing only... the pipelines
# shouldn't fail" — this script IS the pipeline. It is the single source
# of truth for the public-tree allowlist; docs/release-runbook-ashforde.md
# section 10 documents the reasoning, this script is what actually runs.
#
# Safety model ("shouldn't fail" = never publish a broken state, not
# "never encounters an error"):
#   1. Export the allowlist to a scratch dir via `git archive` (never a
#      raw copy — that ships internal docs, see the runbook).
#   2. Run the REAL gate battery INSIDE the export before touching git
#      or GitHub. If anything fails, abort — the public repo is never
#      touched. This step has caught two real bugs that "the allowlist
#      looks right" did not (see runbook section 10, items 1-2).
#   3. Sync a PERSISTENT local mirror clone (never re-init a fresh repo
#      per run — that would force a non-fast-forward push every time,
#      and this project's rule is NEVER force-push without explicit
#      founder authorization). Replace its working tree with the fresh
#      export, commit ON TOP of its existing history, push normally. If
#      the push is rejected (someone pushed to the public repo out of
#      band), STOP and report — do not force.
#   4. No-op if nothing on the allowlist actually changed — safe to run
#      on a timer without spamming empty commits.
#
# Does NOT publish npm or touch the Claude Code plugin channel: the
# plugin channel needs no action (it always resolves live against the
# public repo's default branch, so step 3 alone keeps it current). npm
# is a deliberate, versioned release action with real registry history
# once published — kept OUT of this automatic pipeline on purpose.
# Cut a new npm version with:
#   cd packages/aero-agent-skills && npm version <patch|minor> && npm publish
# from a checkout of the JUST-PUSHED public tree, never from dev HEAD
# directly (numbers must match what's actually public).
#
# Usage:
#   bash ops/automation/publish-public.sh              # sync if changed
#   bash ops/automation/publish-public.sh --dry-run     # export + gate only, never touches the mirror or pushes
set -euo pipefail

DEV_REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLIC_REMOTE="https://github.com/ashfordeOU/aero-agent-skills.git"
MIRROR="$HOME/Code/.aero-agent-skills-public-mirror"
SCRATCH="$(mktemp -d)"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { echo "[publish-public] $(date -u +%FT%TZ) $*"; }
trap 'rm -rf "$SCRATCH"' EXIT

cd "$DEV_REPO"

# --- 0. dev tree itself must be gate-clean before it is worth exporting ---
log "checking dev tree is itself clean (make visuals-check)…"
make visuals-check >/tmp/publish-public-devcheck.log 2>&1 || {
  log "FAIL: dev tree is not visuals-clean — run 'make visuals' first"
  cat /tmp/publish-public-devcheck.log
  exit 1
}

# --- 1. export the allowlist (single source of truth — keep this list in
#        sync with docs/release-runbook-ashforde.md section 3/3b: ship
#        everything scripts/gen_visuals.py's outputs() manages, never
#        marketing/ or the brand-only assets) ---
EXPORT="$SCRATCH/export"
mkdir -p "$EXPORT"
log "exporting public-tree allowlist to ${EXPORT}…"
git archive --format=tar HEAD -- \
  .gitignore .github CITATION.cff CODE_OF_CONDUCT.md CONTRIBUTING.md \
  LICENSE Makefile NOTICE README.md SECURITY.md STANDARDS.md standards-map.yaml \
  .claude-plugin skills scripts eval packages/aero-agent-skills \
  docs/FAQ.md docs/glossary.md docs/harness-contract.md \
  docs/harness-integration.md docs/company-of-departments.md \
  docs/metrics.json docs/DOMAINS.md docs/logo-mark.png \
  docs/title.svg docs/title.png docs/title-dark.svg docs/title-dark.png \
  docs/statline.svg docs/statline.png docs/statline-dark.svg docs/statline-dark.png \
  docs/domain-radar.svg docs/domain-radar.png docs/domain-radar-dark.svg docs/domain-radar-dark.png \
  docs/domain-polar.svg docs/domain-polar.png docs/domain-polar-dark.svg docs/domain-polar-dark.png \
  docs/structure.svg docs/structure.png docs/structure-dark.svg docs/structure-dark.png \
  docs/skill-anatomy.svg docs/skill-anatomy.png docs/skill-anatomy-dark.svg docs/skill-anatomy-dark.png \
  docs/how-it-works.svg docs/how-it-works.png docs/how-it-works-dark.svg docs/how-it-works-dark.png \
  docs/gates.svg docs/gates.png docs/gates-dark.svg docs/gates-dark.png \
  ops/automation ':(exclude)ops/automation/test' \
  | tar -x -C "$EXPORT"
printf 'make validate\nmake attest\nmake visuals-check\nmake package-test\n' > "$EXPORT/.ci-native"

# --- 2. hygiene: secrets + excluded-name leak check (fail closed) ---
# Patterns require a REALISTIC token shape (prefix + a real alnum run),
# not a bare prefix literal — this script itself ships inside the export
# (ops/automation/) and its own source necessarily contains the bare
# strings "ghp_"/"sk-" as pattern text; a bare-prefix match would flag
# itself every run. A prefix immediately followed by 25+ alnum chars is
# never true of the pattern SOURCE, only of an actual leaked token.
log "secrets + leak sweep…"
if grep -rnE 'ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|sk-[A-Za-z0-9]{25,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY' "$EXPORT" 2>/dev/null | grep -q .; then
  log "FAIL: secret-shaped string found in export — aborting, nothing pushed"
  exit 1
fi
if find "$EXPORT" -iname 'social-card*' -o -iname 'ashforde-seal*' -o -iname 'logo-full*' \
     -o -iname 'DESIGN.md' -o -type d -iname 'marketing' -o -iname 'ops-notes.md' \
     -o -iname 'release-runbook-ashforde.md' -o -type d -iname 'superpowers' -o -iname 'AGENTS.md' \
     2>/dev/null | grep -q .; then
  log "FAIL: a marketing/internal-only path leaked into the export — aborting"
  exit 1
fi

# --- 3. prove the export is self-contained: run the REAL gates inside it ---
log "running full gate battery INSIDE the export (several minutes)…"
( cd "$EXPORT" && make validate && make attest && make visuals-check && make package-test ) \
  > /tmp/publish-public-gates.log 2>&1 || {
  log "FAIL: gate battery failed inside the export — NOTHING pushed to the public repo"
  tail -60 /tmp/publish-public-gates.log
  exit 1
}
log "gates green inside the export."

if [ "$DRY_RUN" = 1 ]; then
  log "dry-run: export + gates only, stopping before touching the mirror or GitHub."
  exit 0
fi

# --- 4. sync the persistent mirror clone with the remote (never re-init) ---
if [ -d "$MIRROR/.git" ]; then
  log "syncing existing mirror at $MIRROR with origin/main…"
  git -C "$MIRROR" fetch --quiet origin main
  git -C "$MIRROR" checkout --quiet main
  git -C "$MIRROR" reset --hard --quiet origin/main
else
  log "no local mirror yet — cloning $PUBLIC_REMOTE to ${MIRROR}…"
  git clone --quiet "$PUBLIC_REMOTE" "$MIRROR"
  git -C "$MIRROR" config user.name "ashfordeOU"
  git -C "$MIRROR" config user.email "contact@ashforde.org"
fi

# --- 5. replace the mirror's working tree with the fresh export, diff ---
find "$MIRROR" -mindepth 1 -maxdepth 1 -not -name '.git' -exec rm -rf {} +
cp -a "$EXPORT/." "$MIRROR/"
if git -C "$MIRROR" status --porcelain | grep -q .; then
  : # real changes, continue below
else
  log "no-op: public repo already matches the dev export. Nothing to push."
  exit 0
fi

LEAVES=$(python3 -c "import json; print(json.load(open('$EXPORT/docs/metrics.json'))['leaves'])")
PACKS=$(python3 -c "import json; print(json.load(open('$EXPORT/docs/metrics.json'))['live_packs'])")
FAMILIES=$(python3 -c "import json; print(json.load(open('$EXPORT/docs/metrics.json'))['families'])")

git -C "$MIRROR" add -A
git -C "$MIRROR" commit --quiet -m "sync: ${LEAVES} skills, ${PACKS} packs, ${FAMILIES} families

Automated sync from the private dev/test tree (ops/automation/publish-public.sh).
Gates verified inside this exact export before push: make validate 5/5,
make attest 3/3, make visuals-check, make package-test all green."

log "pushing (normal fast-forward, no force) to ${PUBLIC_REMOTE}…"
if ! git -C "$MIRROR" push --quiet origin main 2>/tmp/publish-public-push.log; then
  log "FAIL: push rejected (public repo has commits this mirror doesn't — investigate before retrying, NEVER force):"
  cat /tmp/publish-public-push.log
  exit 1
fi

REMOTE_HEAD=$(git ls-remote "$PUBLIC_REMOTE" refs/heads/main | cut -f1)
LOCAL_HEAD=$(git -C "$MIRROR" rev-parse HEAD)
if [ "$REMOTE_HEAD" != "$LOCAL_HEAD" ]; then
  log "FAIL: push verification mismatch (remote=$REMOTE_HEAD local=$LOCAL_HEAD)"
  exit 1
fi
log "PASS: public repo updated and verified at $LOCAL_HEAD (${LEAVES} skills, ${PACKS} packs, ${FAMILIES} families)"
