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
# LIVE COPY: ~/.hermes/scripts/aero-campaign-supervisor.sh (the cron --script
# target; cron refuses a symlink that resolves outside its scripts dir).
# This repo copy in ops/automation/ is byte-identical — change both or neither.
set -u

HOME_DIR="${AERO_CAMPAIGN_HOME:-$HOME}"
CAMPAIGN="${AERO_CAMPAIGN_SCRIPT:-$HOME_DIR/company-ops/aero-agent-skills/ops/automation/aero-campaign.sh}"
PATTERN="${AERO_CAMPAIGN_PATTERN:-aero-campaign.sh}"
STOP="${AERO_CAMPAIGN_STOP:-$HOME_DIR/.hermes/state/aero-day-stop}"
LOG="${AERO_CAMPAIGN_LOG:-/tmp/aero-campaign.log}"

stamp() { date -u +%FT%TZ; }

if pgrep -f "$PATTERN" >/dev/null 2>&1; then
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

if pgrep -f "$PATTERN" >/dev/null 2>&1; then
  echo "aero-campaign: restarted from tracked path at $(stamp)"
  exit 0
fi

echo "aero-campaign: RESTART FAILED - no runner 5s after start at $(stamp)"
exit 1
