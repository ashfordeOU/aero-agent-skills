#!/bin/zsh
# TRACKED HOME for the continuous aero campaign (VEDA-0071, 2026-09-11):
# moved verbatim from /tmp/aero-campaign.sh, which was a transient
# `launchctl submit` and survived only until the next reboot or /tmp sweep.
# Started by the LaunchAgent ~/Library/LaunchAgents/aero-campaign.plist
# (RunAtLoad, KeepAlive on non-zero exit). Never start it by hand while the
# agent is loaded - two runners double every wave.
export PATH="$HOME/.local/bin:$PATH"
export AERO_LANE_SIZE=96
export AERO_CONCURRENCY=24
export AERO_MAX_WAVES=60
export AERO_TARGET=0
export AERO_BUILD_TIMEOUT=2400

# DOER GATE (relay 2026-09-11T18:1xZ). This campaign is claude-only: every
# build is a bare `claude -p`. When Claude Code is session-limited each
# session exits instantly ("You've hit your limit"), so a full wave costs a
# lane create/drop, a harvest, a pre-push gate battery and two churn commits
# while producing ZERO leaves (measured: waves 17:33Z / 17:55Z / 18:05Z all
# 926 -> 926). The claude-doer watchdog flips master_switch to "on" when the
# limit resets; wait for that instead of spinning at 2x noise.
#
# CCD lane dispatch inside quiet windows stays allowed (founder GO
# 2026-09-10) - this gate is about the DOER, not the clock.
CONFIG="$HOME/.hermes/state/claude-doer-config.json"
while true; do
  MODE=$(/usr/bin/python3 -c "import json;print(json.load(open('$CONFIG')).get('master_switch',''))" 2>/dev/null)
  [ "$MODE" = "on" ] && break
  echo "$(date -u +%FT%TZ) DOER-GATE: master_switch=$MODE (claude session-limited) - campaign waiting, not burning" >> /tmp/aero-campaign.log
  sleep 300
done

exec /usr/bin/python3 $HOME/.hermes/scripts/aero-day-driver.py >> /tmp/aero-campaign.log 2>&1
