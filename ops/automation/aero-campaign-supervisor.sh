#!/bin/bash
# aero-campaign-supervisor.sh — durable start path for the continuous aero
# campaign (VEDA-0071, 2026-09-11).
#
# WHY THIS EXISTS
# The campaign loop was started with a transient `launchctl submit` of a script
# that lived in /tmp, so a reboot or a /tmp sweep ended it with nothing tracked
# to re-create it. The gateway process blocks `launchctl submit/bootstrap` from
# inside itself (`tools/terminal_tool.py`: "install an explicit LaunchAgent
# from a separate shell"), so the durable start path is this script, fired by
# Hermes cron every 10 minutes from the gateway LaunchAgent (which RunAtLoad-
# starts after a reboot).
#
# CONTRACT: silent no-op while a runner exists (no output, no churn); it only
# ever starts the TRACKED script, and never while the operator stop file is
# present. Two instances can never wave-loop together: aero-day-driver.py holds
# an flock and a duplicate exits cleanly.
#
# LIVENESS — A RUNNER HAS TWO ARGV FORMS, BOTH MUST MATCH (VEDA-0076)
#   1. WAITING at the doer gate: `/bin/zsh <tracked>/aero-campaign.sh`
#   2. RUNNING the campaign:     the wrapper `exec`s the driver, so argv
#      becomes `python3 ~/.hermes/scripts/aero-day-driver.py` and the wrapper
#      name leaves the process table entirely.
# Matching form 1 alone read a live driver (pid 68069) as "no runner", started
# a duplicate, saw the flock refusal as a failure and posted RESTART FAILED to
# the ops topic every 10 minutes for a healthy campaign.
#
# LIVE COPY: ~/.hermes/scripts/aero-campaign-supervisor.sh (the cron --script
# target; cron refuses a symlink that resolves outside its scripts dir).
# This repo copy in ops/automation/ is byte-identical — change both or neither.
set -u

HOME_DIR="${AERO_CAMPAIGN_HOME:-$HOME}"
CAMPAIGN="${AERO_CAMPAIGN_SCRIPT:-$HOME_DIR/company-ops/aero-agent-skills/ops/automation/aero-campaign.sh}"
# Space-separated set of argv patterns that mean "a runner exists".
PATTERNS="${AERO_CAMPAIGN_PATTERN:-aero-campaign.sh aero-day-driver.py}"
STOP="${AERO_CAMPAIGN_STOP:-$HOME_DIR/.hermes/state/aero-day-stop}"
LOG="${AERO_CAMPAIGN_LOG:-/tmp/aero-campaign.log}"

stamp() { date -u +%FT%TZ; }

# True when ANY argv form matches. Word splitting is deliberate: the default is
# a set of two and a test may override it with a single unique token.
running() {
  local pat
  for pat in $PATTERNS; do
    if pgrep -f "$pat" >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

if running; then
  exit 0
fi

if [ -e "$STOP" ]; then
  echo "aero-campaign: stop file present ($STOP) - not starting at $(stamp)"
  exit 0
fi

if [ ! -x "$CAMPAIGN" ]; then
  echo "aero-campaign: RESTART ABORTED - $CAMPAIGN is not executable at $(stamp)"
  exit 1
fi

echo "$(stamp) SUPERVISOR: no runner found - starting tracked campaign $CAMPAIGN" >> "$LOG"
nohup /bin/zsh "$CAMPAIGN" >> "$LOG" 2>&1 &
sleep 5

if running; then
  echo "aero-campaign: restarted from tracked path at $(stamp)"
  exit 0
fi

echo "aero-campaign: RESTART FAILED - no runner 5s after start at $(stamp)"
exit 1
