#!/usr/bin/env bash
# Hourly umbrella: sync the public repo, then the landing page. Founder
# 2026-09-02: domain coverage "will keep increasing every hour" — both
# downstream surfaces (github.com/ashfordeOU/aero-agent-skills and
# ashforde.org/aeroagentskills) need to track dev HEAD without manual
# reruns. Driven by launchd (org.ashforde.aero-hourly-publish, see
# ~/Library/LaunchAgents), logged to ~/Library/Logs/aero-hourly-publish.log.
#
# Best-effort between the two steps: a failure in one does not block the
# other (they publish to different repos), but each step's OWN gate
# battery is still fail-closed — neither script will ever push a broken
# state, they just abort and log instead of throwing away the other
# surface's chance to update.
#
# Founder 2026-09-02: "focus on maintaining public repo from now on...
# make the public repo update the states on the site" — step 2 now
# pulls the landing page's metrics straight from the PUBLIC repo's main
# branch (raw.githubusercontent.com), not the local dev tree, so it
# only ever shows what is actually live and public. Step 1 still exists
# to carry any future dev-tree fix out to the public repo; it is not
# run on a content-growth cadence anymore.
set -uo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "===== $(date -u +%FT%TZ) hourly-publish starting ====="

echo "--- public repo sync ---"
if ! bash /Users/chak/Code/aeroskills/ops/automation/publish-public.sh; then
  echo "!!! public repo sync FAILED — see above, nothing was published to ashfordeOU/aero-agent-skills"
fi

echo "--- landing page sync ---"
if ! bash /Users/chak/Documents/Code/Claudecode/ashforde-site/aeroagentskills/sync-and-publish.sh; then
  echo "!!! landing page sync FAILED — see above, ashforde.org/aeroagentskills not updated"
fi

echo "===== $(date -u +%FT%TZ) hourly-publish done ====="
