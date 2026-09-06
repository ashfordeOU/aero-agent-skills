#!/usr/bin/env bash
# Hourly umbrella for every aero-* product's public surfaces. Driven by
# launchd (org.ashforde.aero-hourly-publish, see ~/Library/LaunchAgents),
# logged to ~/Library/Logs/aero-hourly-publish.log.
#
# Best-effort between steps: a failure in one does not block the others
# (they publish to different repos/pages), but each step's OWN gate
# battery is still fail-closed — no script here will ever push a broken
# state, it just aborts and logs instead of throwing away another
# surface's chance to update.
#
# Founder 2026-09-02: "focus on maintaining public repo from now on...
# make the public repo update the states on the site" — every landing-page
# sync below pulls straight from its PUBLIC repo's main branch
# (raw.githubusercontent.com), never a private dev tree, so a page only
# ever shows what is actually live and public. aero-agent-skills has both
# an active publish-public.sh (step 1) and a live public repo; aero-agent-
# roles (step 3) has neither yet — its sync-and-publish.sh cleanly no-ops
# until that pipeline exists (founder 2026-09-05: the roles site "has to
# only run via Public site when it's live").
set -uo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# Machine-portable on purpose: this script has been hand-edited with a
# different developer's absolute home directory more than once by
# concurrent sessions on different machines, each silently breaking the
# other's launchd job. publish-public.sh is a sibling in this same repo,
# so it's found relative to this script's own location, not hardcoded.
# The site repo is a genuinely separate clone whose location is
# machine-specific — override with ASHFORDE_SITE_REPO (e.g. in the
# launchd plist's EnvironmentVariables) rather than hand-editing this
# file; the default below is only a fallback for whichever machine
# hasn't set it.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_REPO="${ASHFORDE_SITE_REPO:-$HOME/Documents/Code/Claudecode/ashforde-site}"

echo "===== $(date -u +%FT%TZ) hourly-publish starting ====="

echo "--- public repo sync ---"
if ! bash "$SCRIPT_DIR/publish-public.sh"; then
  echo "!!! public repo sync FAILED — see above, nothing was published to ashfordeOU/aero-agent-skills"
fi

echo "--- landing page sync (skills) ---"
if ! bash "$SITE_REPO/aeroagentskills/sync-and-publish.sh"; then
  echo "!!! landing page sync FAILED — see above, ashforde.org/aeroagentskills not updated"
fi

# aero-agent-roles has no publish-public.sh yet, so ashfordeOU/aero-agent-roles
# is still empty — sync-and-publish.sh's own sync-metrics.sh detects that and
# cleanly no-ops (exit 0) rather than erroring. The moment that pipeline
# starts pushing packages/aero-agent-roles/manifest.json + docs/*.png to the
# public repo, this step starts actually updating the roles landing page,
# with no further change needed here.
echo "--- landing page sync (roles) ---"
if ! bash "$SITE_REPO/aeroagentroles/sync-and-publish.sh"; then
  echo "!!! landing page sync FAILED — see above, ashforde.org/aeroagentroles not updated"
fi

echo "===== $(date -u +%FT%TZ) hourly-publish done ====="
