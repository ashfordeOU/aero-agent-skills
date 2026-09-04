---
name: holding-pattern-entry
description: "Use when you must determine a holding pattern entry: classify the maneuver for joining a holding fix as direct, teardrop, or parallel from the angle between the inbound track and the holding side using the standard 70/110 degree sector rule, compute the outbound leg timing from the holding altitude (1 minute at or below 14000 ft, 1.5 minutes above), correct the outbound heading for crosswind with the 1-in-60 rule, and estimate the first entry lap time. Produces the entry type, outbound leg seconds, wind-corrected outbound heading, and entry-lap time estimate for FMS or manual hold joining. Trigger: holding-pattern-entry, direct-entry-sector, teardrop-entry-sector, parallel-entry-sector, outbound-leg-timing, holding-wind-correction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: avionics
pack: flight-management
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [holding-pattern-entry, direct-entry-sector, teardrop-entry-sector, parallel-entry-sector, outbound-leg-timing, holding-wind-correction]
  version: 0.1.0
  author: AeroSkills
---

# Holding Pattern Entry (avionics/flight-management/holding-pattern-entry)

Use when the task is determining how an aircraft joins a holding pattern:
classifying the entry maneuver as direct, teardrop or parallel from the
geometry of the approach to the holding side, timing the outbound leg
from the holding altitude, correcting the outbound heading for the
crosswind, and estimating the duration of the first (entry) lap. This
leaf implements the standard 70/110 degree entry sector rule and the
standard hold timing rules in pure Python, stdlib only. It pairs with
avionics/flight-management/flight-planning for the route structure that
carries the hold fix, avionics/flight-management/lateral-navigation for
the track guidance that flies the pattern legs, and
avionics/flight-management/performance-computation for the speed
selection context.

## Domain quick reference

- Geometry convention: alpha_deg is the smaller angle from the inbound
  course (the course flown TOWARD the fix) to the OUTBOUND end of the
  holding radial, measured on the holding side, in [0, 180] degrees.
  The holding side is right-hand or left-hand.
- Entry sector rule (standard operational procedure, paraphrased):
  alpha <= 70 deg is a direct entry, 70 < alpha <= 110 deg is a
  teardrop entry, alpha > 110 deg is a parallel entry. A left-hand hold
  mirrors the sectors, so alpha measured on the holding side applies
  the same thresholds.
- Outbound leg timing: 60 s at or below 14000 ft, 90 s above (1 minute
  at or below 14000 ft, 1.5 minutes above; 14000 ft itself takes the
  60 s leg).
- 1-in-60 wind correction: the crosswind component is wind_speed_kt *
  sin(radians(wind_from_deg - outbound_heading_deg)), positive when the
  wind blows from the right of the outbound heading; the drift angle in
  degrees is 60 * crosswind_component / tas_kt (a 1 kt crosswind at
  60 kt TAS is about 1 degree of drift); the corrected heading is
  (outbound_heading + correction) mod 360, steering back into the wind.
- Entry lap time (documented model): the first lap counts ONE timed
  outbound leg plus a fixed sector-geometry offset: +180 s (3 minutes)
  for a direct entry, +240 s (4 minutes) for a teardrop entry, +300 s
  (5 minutes) for a parallel entry. The extra minute blocks absorb the
  additional turns and inbound segments of the more complex entry
  maneuvers.
- FAR 25 frames the airworthiness context for the FMS procedure
  function; the entry sector rule above is operational procedure,
  summary-only, never reproduced from a standard.
- Units are mixed by convention: degrees for angles and headings,
  feet for altitude, knots for speeds, seconds for the time outputs.

## Workflow

1. Fix the hold geometry: confirm the holding side (right or left) and
   measure alpha, the angle from the inbound course to the outbound end
   of the holding radial on the holding side.
2. Classify the entry with entry_type(alpha_deg, turn_direction), which
   returns direct, teardrop or parallel from the 70/110 degree sector
   rule.
3. Time the outbound leg with outbound_leg_seconds(altitude_ft),
   returning 60 s at or below 14000 ft and 90 s above.
4. Correct the outbound heading with
   wind_correction_heading(outbound_heading_deg, wind_from_deg,
   wind_speed_kt, tas_kt); the sign of the correction follows the wind
   direction through the sine term and the result normalizes to
   [0, 360).
5. Estimate the first lap with entry_lap_time_seconds(entry,
   outbound_leg_seconds), one outbound leg plus the entry offset.
6. Confirm the deterministic checks with the contract test
   scripts/test_holding_pattern_entry.py.

## Worked example

Right-hand hold, inbound course chosen so that alpha = 50 deg gives a
direct entry, alpha = 90 deg a teardrop and alpha = 130 deg a parallel
entry.

- Entry classification (real module outputs): entry_type(50.0,
  "right") = "direct"; entry_type(90.0, "right") = "teardrop";
  entry_type(130.0, "right") = "parallel". The 70 and 110 degree
  boundaries themselves classify as direct and teardrop respectively.
- Outbound leg timing: outbound_leg_seconds(12000.0) = 60.0 s and
  outbound_leg_seconds(20000.0) = 90.0 s; at the threshold,
  outbound_leg_seconds(14000.0) = 60.0 s while
  outbound_leg_seconds(14001.0) = 90.0 s.
- Wind correction: outbound heading 090, wind from 135 at 20 kt, TAS
  180 kt. Crosswind = 20 * sin(45 deg) = 14.14 kt, correction =
  14.14 / 180 * 60 = 4.71 deg, corrected heading 094.7.
  wind_correction_heading(90.0, 135.0, 20.0, 180.0) = 94.7140 deg. A
  wind 180 degrees opposite (from 315) gives
  wind_correction_heading(90.0, 315.0, 20.0, 180.0) = 85.2860 deg, the
  sign reversed, and the two corrected headings sum to 180 deg.
- Entry lap at 12000 ft, direct: entry_lap_time_seconds("direct",
  60.0) = 240.0 s (60 s outbound plus 180 s offset). The teardrop and
  parallel laps at the same altitude are 300.0 s and 360.0 s; with the
  90 s leg at 20000 ft they become 270.0 s, 330.0 s and 390.0 s.

## Verification

- Confirm entry_type(50.0, "right") = "direct", entry_type(90.0,
  "right") = "teardrop" and entry_type(130.0, "right") = "parallel",
  and that a left-hand hold returns the same classes for alpha measured
  on its holding side.
- Confirm outbound_leg_seconds is 60.0 at 14000 ft and 90.0 just above
  (14001 ft), per the 1 minute / 1.5 minute rule.
- Confirm wind_correction_heading(90.0, 135.0, 20.0, 180.0) returns
  94.7140 deg, within 0.1 deg of the 4.71 deg correction anchor, and
  that a wind 180 degrees opposite reverses the correction sign.
- Confirm entry_lap_time_seconds("direct", 60.0) = 240.0 s for the
  worked example and the documented offset identity: lap time minus the
  outbound leg equals 180, 240 or 300 s by entry type.
- Confirm ValueError rejection of non-physical inputs: alpha outside
  [0, 180], a turn direction other than right or left, negative
  altitude, non-positive TAS, negative wind speed, an unknown entry
  string, and a non-positive outbound leg time.
- Run the contract test offline: python3
  scripts/test_holding_pattern_entry.py (35 tests, deterministic).

## Pitfalls

- Measuring alpha on the wrong side: alpha must be measured on the
  holding side. For a left-hand hold the same 70/110 degree thresholds
  only apply when alpha is measured on the left; measuring the
  non-holding side angle mirrors the geometry and misclassifies the
  entry sector.
- Putting 14000 ft in the wrong tier: the timing boundary is at or
  below 14000 ft (60 s) versus above (90 s), so the threshold itself
  takes the 1 minute leg.
- Dropping the wind correction sign: the correction is added toward the
  wind and its sign comes from the sine of (wind_from - outbound
  heading), so a wind from the left of the outbound heading subtracts
  from the heading rather than adding to it.
- Using a raw heading sum: the corrected heading must be normalized to
  [0, 360), so a heading near 360 wraps (359 deg plus a 6.7 deg
  correction reports 5.7 deg, not 365.7 deg).
- Counting the full pattern instead of the entry lap: the first lap
  model counts one timed outbound leg plus the entry offset, so a
  parallel entry (360 s at 12000 ft) runs 120 s longer than a direct
  entry (240 s) at the same altitude.
- Confusing the hold geometry with sibling leaves: route and leg
  distance construction, track guidance, curved-leg path geometry and
  waypoint time control are separate leaves that consume or fly the
  hold but do not classify its entry.

## Related leaves

- avionics/flight-management/flight-planning: the route structure that
  carries the holding fix and its legs.
- avionics/flight-management/lateral-navigation: the track guidance
  that flies the inbound and outbound legs of the pattern.
- avionics/flight-management/radius-to-fix-leg: the curved path
  geometry used between fixes in the terminal area.
- avionics/flight-management/rta-time-control: the speed command
  function that meets a time constraint at a downstream waypoint.
- avionics/flight-management/performance-computation: the speed
  selection context for the hold and the approach.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_holding_pattern_entry.py

The test covers the 70/110 degree entry truth table including both
boundaries and left-hand mirroring, the outbound leg timing truth table
at 14000 ft and just above, the 1-in-60 wind correction anchor (4.71
deg within 0.1 deg at the worked example) and its sign reversal for a
wind 180 degrees opposite, heading normalization to [0, 360), wind
speed scaling of the correction, the entry-lap time offsets and their
documented identity, float output types, repeat-call determinism, and
ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: FAR 25 is the family spine for
  the FMS procedure context (reference-only per standards-map.yaml);
  the 70/110 degree entry rule and the hold timing rules are named as
  operational procedure, paraphrased, never reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.
