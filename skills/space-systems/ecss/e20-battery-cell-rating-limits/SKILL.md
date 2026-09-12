---
name: e20-battery-cell-rating-limits
description: "Use when define the maximum cell ratings that ECSS-E-ST-20C clause 5.6.3 requires a battery design to hold, and verify a duty profile against them: hold a temperature window, a charge ceiling and a discharge floor voltage, and charge, discharge and storage current limits for every operating mode; tighten the whole set through a derating policy of voltage and current factors plus a thermal margin; then examine each declared operating point mode by mode, name the parameter with the least normalized margin, and list every exceedance. Trigger: ecss, e-st-20-electrical-scope, e20-battery-cell-rating-limits, cell-rating-envelope, charge-current-limit, discharge-current-limit, cell-voltage-ceiling, cell-temperature-window, cell-derating-policy, c-rate-limit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e20-battery-cell-rating-limits, cell-rating-envelope, charge-current-limit, discharge-current-limit, cell-voltage-ceiling, cell-temperature-window, cell-derating-policy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Battery Cell Rating Limits (space-systems/ecss/e20-battery-cell-rating-limits)

Use when the task is fixing the maximum cell ratings of ECSS-E-ST-20C clause
5.6.3 -- temperature, voltage and charge or discharge current -- into a single
envelope, and showing that every operating point the battery is asked to reach
stays inside it.

## Domain quick reference

- The rating set is three parameters and three modes, and the mode changes the
  limit. A cell that tolerates a wide discharge temperature range usually
  accepts a much narrower one for charge, because plating and gassing are
  charge-side mechanisms; a current the cell delivers on discharge can be
  several times the current it will accept on charge; and in storage neither a
  charge nor a discharge current is admissible at all, only leakage.
- Voltage is bounded differently per mode too. Charge is bounded above by the
  end-of-charge ceiling; discharge is bounded below by the cut-off floor and
  still above by the same ceiling, since a terminal voltage over it means the
  measurement or the topology is wrong. The floor must sit below the ceiling
  for the rating set to describe a usable cell at all.
- Currents are best read as C-rates: the current divided by the ampere-hour
  capacity. The same 10 A is a gentle 0.5C on a 20 Ah cell and an abusive 5C on
  a 2 Ah one, so a limit quoted in amperes only is meaningful against a stated
  capacity, and the capacity belongs in the rating set beside the limits.
- Derating narrows the envelope before the design uses it: the voltage ceiling
  comes down by a factor, the discharge floor rises by the same factor, the
  current limits scale down, and both ends of every temperature window pull in
  by a thermal margin. A policy aggressive enough to invert a window is a
  policy defect, not a very tight design.
- A point that passes on every parameter is not equally close to all of them.
  Normalizing each margin by the span of its own limit makes temperature,
  voltage and current comparable, so the envelope assessment can name which
  parameter is actually driving the design rather than reporting three
  unranked passes.

## Workflow

1. Assemble the rating set: chemistry, ampere-hour capacity, a temperature
   window for charge, discharge and storage, the end-of-charge voltage ceiling
   and the discharge voltage floor, and the maximum charge, discharge and
   storage leakage currents. Reject a missing mode, an inverted window, a floor
   at or above the ceiling, and a non-positive capacity or current limit.
2. Apply the derating policy if one is in force: scale the voltage ceiling and
   the current limits down by their factors, raise the discharge floor by the
   voltage factor, and pull both ends of every temperature window in by the
   thermal margin. Reject a policy that collapses any window.
3. For each declared operating point, read its mode and select the limits that
   mode imposes: the temperature window for that mode, the voltage bounds that
   apply to it, and the single current limit that bounds it.
4. Compute a margin per parameter -- the distance to the nearer limit -- and
   normalize it by the span of that limit so the three are comparable. A
   non-negative margin is inside, a point exactly on a limit is inside, a
   negative margin is an exceedance.
5. Record each point's exceedances and its limiting parameter, then aggregate
   over the duty profile: the worst normalized margin names the point and the
   parameter that drive the design, and the profile is inside the envelope only
   when no point produced an exceedance.
6. Re-run the assessment whenever the derating policy or the capacity changes,
   since both move every C-rate and every margin in the set.

## Pitfalls

- Carrying one temperature window for the whole cell -- the charge window is
  typically the narrow one, so a single window either forbids valid discharge
  operation or permits charging at a temperature that damages the cell.
- Quoting current limits in amperes with no capacity beside them -- the limit
  is a C-rate in disguise, and reusing an ampere figure from a different cell
  size silently changes the stress by the ratio of the capacities.
- Treating storage as a third temperature window and nothing more -- a store
  parked on a bus that trickles into it is not in storage, and the leakage
  limit is the check that catches it.
- Applying a derating factor only to the upper limits -- the discharge floor is
  a limit too, and leaving it unrated while the ceiling comes down quietly
  widens the usable window instead of narrowing it.
- Comparing raw margins across parameters and concluding that 20 K of thermal
  margin beats 0.05 V of voltage margin -- against their own spans the voltage
  is the tighter of the two by a factor of thirty, and only the normalized
  comparison shows it.

## Behavior contract (gate 3)

The rating-set validation, derating, per-mode temperature, voltage and current
checks, normalized-margin ranking and duty-profile aggregation are exercised by
the gate 3 contract test: scripts/test_e20_battery_cell_rating_limits.py
against scripts/e20_battery_cell_rating_limits_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e20_battery_cell_rating_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
