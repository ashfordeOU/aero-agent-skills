---
name: tcas-resolution-advisory
description: "Use when you must evaluate a TCAS II resolution advisory for an own aircraft against a single intruder from measured range and altitude state: select the sensitivity level from the own altitude band, compute the modified tau closing time with the DMOD term, apply the horizontal threat test and the altitude test against the tau and ALIM thresholds, and choose the climb or descend advisory sense from the intruder position. Produces the sensitivity level, the modified tau, the threat verdict and the resolution advisory sense that gate a TCAS logic assessment. Trigger: TCAS II, traffic alert and collision avoidance, resolution advisory, modified tau, DMOD, sensitivity level, intruder threat logic, climb descend advisory."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-185
    reference-only: true
gated: false
domain: avionics
pack: surveillance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: surveillance
  tags: [tcas-resolution-advisory, traffic-alert-collision-avoidance, modified-tau, sensitivity-level, intruder-threat-logic, resolution-advisory-sense, dmod-cylinder]
  version: 0.1.0
  author: Aero Agent Skills
---

# TCAS II Resolution Advisory (avionics/surveillance/tcas-resolution-advisory)

Use when the task is evaluating a TCAS II traffic alert and collision
avoidance resolution advisory for an own aircraft against one intruder,
starting from already-measured range, range rate and altitude state: pick
the sensitivity level from the own altitude band, compute the modified tau
closing-time metric with the distance-modified DMOD term, apply the
horizontal threat test and the altitude test, and choose the climb or
descend RA sense. This leaf is the first of the avionics/surveillance
pack, which frames airborne surveillance logic; future siblings may add
ADS-B or transponder functions. It pairs with
avionics/flight-management/rnp-anp-containment for separation assurance in
the flight management system, avionics/flight-management/lateral-navigation
for the route guidance an RA overrides, and
avionics/flight-management/radio-navigation-aids for the navaid sensors.

The boundary matters: this leaf is the threat and sense logic on measured
state, not the transponder waveform, not the FMS route, not a datalink
transport. The MOPS parameters below are paraphrased DO-185B summary
values, never a reproduction of the proprietary tables. Pure Python
stdlib, deterministic and offline. Units follow the avionics standard:
range in nautical miles, range rate in nautical miles per second,
altitude in feet, closing speed in knots, time in seconds.

## Domain quick reference

- Sensitivity level selection: the own altitude band index, lower bound
  inclusive and upper bound exclusive, with boundaries at 1000, 2350,
  5000, 10000 and 20000 ft selecting sensitivity levels 2 through 7 above
  sea level. Level 1 exists only as an inhibited low-altitude state below
  the model; the table used here starts at level 2.
- Per-level thresholds (paraphrased values, exact numbers live in the
  SENSITIVITY_TABLE module constant in the logic file): tau (the
  horizontal tau threshold) grows from 20 s at level 2 to 48 s at level
  7, DMOD grows from 0.30 to 1.10 nmi, and ALIM (the altitude test limit)
  grows from 300 to 600 ft.
- Modified tau: tau_mod = -(range^2 - DMOD^2) / (range * range_rate),
  where range is in nmi and range_rate is negative for a closing
  encounter. When the range already lies at or inside the DMOD cylinder
  the modified tau collapses to 0.0 and the encounter is an immediate
  horizontal threat. The DMOD term removes the singularity at small
  range, so tau_mod stays finite down to the cylinder.
- Horizontal threat test: tau_mod <= tau for the active sensitivity
  level, a closing-time check that keeps long, slow encounters out of the
  advisory.
- Altitude test: the vertical separation |dh| between the intruder and
  the own aircraft must stay within ALIM for the advisory to fire.
- RA sense: descend when the intruder sits above the own aircraft and
  climb when it sits at or below it, so the advisory always moves the own
  aircraft away from the intruder. A tie at equal altitude resolves to
  climb.
- Threat verdict: a closing encounter that passes the horizontal test and
  the altitude test is a threat; otherwise the verdict carries the
  failing gate as the reason, "tau-exceeded" or "altitude-exceeded", and
  a non-closing encounter reports "not-closing" with no modified tau.

## Workflow

1. Fix the encounter state: range in nmi, closing range rate in nmi/s
   (negative when closing), own altitude in ft, intruder altitude in ft.
   Convert a closing speed in knots to nmi/s by dividing by 3600 before
   calling the functions.
2. Select the sensitivity level with sensitivity_level(own_altitude_ft);
   the returned level keys the SENSITIVITY_TABLE thresholds (tau, DMOD,
   ALIM).
3. For a closing encounter, compute the modified tau with
   modified_tau(range_nmi, range_rate_nmi_s, dmod_nmi). A range at or
   inside DMOD returns 0.0, which is an immediate horizontal threat.
4. Run threat_verdict(range_nmi, range_rate_nmi_s, own_altitude_ft,
   intruder_altitude_ft) for the full verdict dict: sensitivity level,
   tau threshold, DMOD, ALIM, modified tau, the threat flag and either
   the sense or the reason. Non-closing encounters are gated here before
   the modified tau is called.
5. Read the sense with ra_sense(intruder_altitude_ft,
   own_altitude_ft), or take the whole chain from
   evaluate_encounter(range_nmi, range_rate_nmi_s, own_altitude_ft,
   intruder_altitude_ft), which returns sensitivity_level, modified_tau,
   threat, the reason or the sense, the resolution_advisory ("climb",
   "descend" or "none") and the active parameters.
6. Confirm the deterministic checks with the contract test
   scripts/test_tcas_resolution_advisory.py.

## Worked example

Own aircraft at 8000 ft, which selects sensitivity level 5 (tau 40 s,
DMOD 0.75 nmi, ALIM 350 ft), closing at 300 kt (range rate -0.08333
nmi/s).

- Case 1: range 3.0 nmi, intruder at 8200 ft (200 ft above). Modified
  tau: -(9 - 0.5625) / (3 * -0.08333) = 33.75 s, within the 40 s tau
  gate, and |dh| 200 ft within ALIM 350 ft: threat True, sense "descend",
  resolution_advisory "descend".
- Case 2: range 8.0 nmi, intruder at 8200 ft. Modified tau 95.16 s
  exceeds 40 s: threat False with reason "tau-exceeded" and
  resolution_advisory "none"; the closing time is still too long for an
  advisory.
- Case 3: range 2.0 nmi, intruder at 7800 ft (200 ft below). Modified tau
  20.63 s passes the tau gate: threat True, sense "climb".
- Case 4 (high altitude): own aircraft at 30000 ft (sensitivity level 7,
  tau 48 s, DMOD 1.10 nmi, ALIM 600 ft), range 5.0 nmi closing at 180 kt
  (range rate -0.05 nmi/s), intruder 500 ft below. Modified tau 95.16 s
  exceeds 48 s: threat False with reason "tau-exceeded" even though the
  500 ft separation sits inside ALIM 600 ft. The tau gate protects the
  own aircraft at long range.
- Case 5: own aircraft at 5000 ft (level 5), range 1.0 nmi closing at 300
  kt, intruder 100 ft above. The range hugs the DMOD influence, modified
  tau 5.25 s passes the tau gate: threat True, sense "descend".
- ValueErrors: a negative altitude, a non-positive range or DMOD, and a
  non-negative range rate passed directly to modified_tau all raise
  ValueError; evaluate_encounter propagates them unchanged.

## Verification

- sensitivity_level(8000) returns 5, sensitivity_level(500) returns 2 and
  sensitivity_level(30000) returns 7.
- The band edges sit at 999/1000, 2349/2350, 4999/5000, 9999/10000 and
  19999/20000 ft, with the upper boundary belonging to the higher band.
- The five worked cases reproduce the anchors: modified tau 33.75, 95.16,
  20.63, 95.16 and 5.25 s within 0.01 s, with the stated threat flags,
  reasons and senses.
- A non-closing or opening range rate produces reason "not-closing" with
  modified_tau None and never reaches the modified tau function.
- Range at or inside DMOD returns modified tau 0.0.
- Sense selection: intruder above gives descend, intruder below gives
  climb, and an equal-altitude tie resolves to climb.
- Every non-physical input raises ValueError: negative altitude,
  non-positive range, non-positive DMOD, non-negative range rate.
- Run the contract test offline: python3
  scripts/test_tcas_resolution_advisory.py (31 tests, deterministic).

## Related leaves

- avionics/flight-management/rnp-anp-containment: separation assurance
  against the RNP containment bound in the FMS context.
- avionics/flight-management/lateral-navigation: the route guidance a
  resolution advisory overrides during the maneuver.
- avionics/flight-management/radio-navigation-aids: VOR, DME and ILS
  geometry, the surveillance and navigation context around the TCAS
  logic.
- avionics/data-bus/arinc429-protocol: the data bus transport that can
  carry the measured state, distinct from the threat logic itself.

## Pitfalls

- Flipping the range-rate sign: range rate is negative for a closing
  encounter and tau_mod = -(range^2 - DMOD^2) / (range * range_rate)
  needs that closing sign - a closing speed in knots must be divided
  by 3600 before calling, and a non-negative (opening) rate is the
  "not-closing" gate, which never reaches the modified tau function
  and raises ValueError if passed to it directly.
- Assigning the sensitivity band edges to the wrong side: each own
  altitude band is lower-inclusive and upper-exclusive (boundaries at
  1000, 2350, 5000, 10000 and 20000 ft), so 8000 ft selects level 5
  and 500 ft selects level 2 while the low-altitude level 1 is an
  inhibited state outside the model - a 1000 ft aircraft belongs to
  the level 3 band, not level 2.
- Dividing by range rate inside the DMOD cylinder: once the range sits
  at or inside DMOD the modified tau collapses to 0.0 and the
  encounter is an immediate horizontal threat - the DMOD term exists
  to remove the small-range singularity, so never evaluate the raw
  quotient inside the cylinder.
- Reading a False threat as a clean bill: the verdict always carries
  the failing gate, "tau-exceeded" or "altitude-exceeded", and a
  closing encounter that fails the tau test can still sit inside
  ALIM - case 4's 95.16 s against the 48 s tau at level 7 fails even
  with 500 ft of vertical separation inside the 600 ft ALIM, and
  long, slow encounters are exactly what the tau gate is for.
- Reversing the advisory sense: the own aircraft descends when the
  intruder sits above it and climbs when the intruder is at or below
  it (equal altitude resolves to climb) - the sense always moves the
  own aircraft away from the intruder, so swapping the comparison
  commands a climb into a higher intruder.
- Using one threshold set for every altitude: tau (20 to 48 s), DMOD
  (0.30 to 1.10 nmi) and ALIM (300 to 600 ft) grow with the
  sensitivity level selected from own altitude - level 5 at 8000 ft
  runs tau 40 s, DMOD 0.75 nmi, ALIM 350 ft, and the values in
  SENSITIVITY_TABLE are paraphrased teaching values, never the MOPS
  tables of rtca-do-185b.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_tcas_resolution_advisory.py

The test covers the sensitivity level band edges and worked anchors, the
five spec cases with their modified tau values, threat verdicts and climb
or descend senses, the not-closing gate, the tau-exceeded versus
altitude-exceeded reasons, sense selection in both directions with ties to
climb, the full evaluate_encounter chain with its parameters dict, and
ValueError rejection of negative altitude, non-positive range and DMOD,
and non-closing range rate.

## Compliance

- RTCA DO-185B (Minimum Operational Performance Standards for TCAS II
  Airborne Equipment, EUROCAE twin ED-143) is referenced, not reproduced:
  it is a proprietary RTCA document, and the sensitivity level parameters
  shown here are paraphrased summary values for teaching, never the MOPS
  tables. The modified tau and threat test relations are the standard
  engineering method in summary form.
- compliance: STANDARDS-REF, gated: false.
