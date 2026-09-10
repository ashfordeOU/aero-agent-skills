#!/usr/bin/env bash
# Founder-GO hold for the PUBLIC publish (Ruling 3: no public pushes without
# founder GO). Fail-closed: absent or blank GO file => HELD.
#
# The GO file lives OUTSIDE the repo (host-local state), so a GO can never be
# committed, exported, or mistaken for release content:
#   default:  $HOME/.hermes/state/aero-public-publish-GO
#   override: AERO_PUBLISH_GO_FILE   (tests use a temp path)
#
# Contract: exit 0 = GO present (publish authorized) · exit 78 = HELD.
# One line is printed naming the decision and the GO file, so every caller's
# log carries WHY a publish did or did not happen.
set -uo pipefail

GO_FILE="${AERO_PUBLISH_GO_FILE:-$HOME/.hermes/state/aero-public-publish-GO}"

if [ ! -f "$GO_FILE" ]; then
  echo "HELD: no founder GO at $GO_FILE — public publish not authorized (Ruling 3)."
  echo "      Authorize a release with: printf 'GO <scope> <date>' > $GO_FILE"
  exit 78
fi

if [ ! -s "$GO_FILE" ]; then
  echo "HELD: founder GO file $GO_FILE is EMPTY — an empty GO is not a GO (fail-closed, Ruling 3)."
  exit 78
fi

echo "GO: public publish authorized by $GO_FILE — $(head -c 200 "$GO_FILE" | tr '\n' ' ')"
exit 0
