---
name: ewis-installation-quality
description: "Use when you must verify the installation quality of an electrical wiring interconnection system (EWIS) installation during aerospace assembly: compute the conductor bundle fill ratio against the conduit cross-section and check it against the 0.40 fill limit, compute the round-trip voltage drop of the run and its percent of the bus voltage against the 2% drop limit, check the conductor bend radius against the minimum radius factor, and check the separation clearance between the bundle and a nearby fluid line or structure. Produces the fill-ratio, voltage-drop-check, bend-radius-check and separation verdicts that gate an EWIS installation acceptance. Trigger: ewis-installation, wiring-harness, bundle-fill-ratio, voltage-drop-check, bend-radius-check, separation-clearance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: assembly
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: assembly
  tags: [ewis-installation-quality, wiring-harness, bundle-fill-ratio, voltage-drop-check, bend-radius-check, separation-clearance]
  version: 0.1.0
  author: Aero Agent Skills
---

# EWIS Installation Quality (manufacturing-quality/assembly/ewis-installation-quality)

Use when the task is verifying the physical installation quality of an
electrical wiring interconnection system (EWIS) bundle during aerospace
assembly: checking that the conductor bundle does not overfill its
conduit or clamp cross-section, that the round-trip voltage drop of a
power or signal run stays within its percent-of-bus limit, that no
conductor bend is tighter than the minimum radius factor allows, and
that the bundle keeps the required separation clearance from nearby
hydraulic or fuel lines and structure. This leaf implements the four
checks in pure Python, stdlib only; the wire gauge, resistance per
meter and current are inputs, and the geometry, fill, drop, bend and
separation verdicts are the outputs. It is the second leaf of the
assembly pack and pairs with manufacturing-quality/assembly/fastener-
installation-quality, which owns the structural side of the same
acceptance step. EWIS design tasks that select the harness routing or
splice layout are out of scope here.

## Domain quick reference

- Wire area: A = PI * (d / 2)^2 for a round conductor of diameter d,
  with PI = math.pi. Areas add across the bundle.
- Bundle fill ratio: fill = sum(A_i) / A_conduit, the summed conductor
  area over the conduit inner area. New-install limit FILL_LIMIT =
  0.40; the check passes when fill <= limit (fill exactly at the limit
  passes), margin = limit - fill.
- Round-trip resistance: R_rt = 2 * R_per_m * L. The return path
  doubles the one-way resistance of a run of length L.
- Voltage drop: drop_V = I * R_rt and drop_pct = 100 * drop_V / V_bus.
  Default acceptance limit VOLTAGE_DROP_LIMIT_PCT = 2.0 percent of the
  nominal bus voltage; margin = limit - drop_pct.
- Bend radius: required = BEND_FACTOR_DEFAULT * conductor_diameter with
  BEND_FACTOR_DEFAULT = 6.0 (typical shielded bundle minimum, a factor
  of the conductor diameter). Verdict margin = actual / required - 1;
  a negative margin fails.
- Separation: margin = actual / required - 1 for the distance between
  the bundle and a fluid line or structure; a negative margin fails.
- Fill, drop, bend and separation all compare with a <= style pass
  (margin >= 0 passes), so the four verdicts combine into one
  overall_pass with the failing checks named.
- Units are consistent mm for diameters and radii, m for run length,
  ohm/m for resistance per meter, V for voltage, A for current, mm for
  distances, percent for the drop.
- AS9100 frames the manufacturing acceptance context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Gather the run inputs: bus voltage, the conductor diameters of the
   bundle (wire_diameters), the conduit inner diameter, resistance per
   meter, run length, load current, actual bend radius, and the actual
   and required separation distances.
2. Compute the fill with bundle_fill_ratio and get the verdict from
   fill_check against fill_limit (default FILL_LIMIT).
3. Compute the round-trip resistance with round_trip_resistance, feed
   it to voltage_drop with the bus voltage and current, and compare the
   drop_pct output against drop_limit_pct in the report.
4. Check the bend with bend_radius_check(conductor_diameter,
   actual_bend_radius, factor): the largest single conductor in the
   bundle drives the required radius (worst case).
5. Check the separation with separation_check(actual_distance,
   required_distance).
6. Aggregate everything with ewis_installation_report in one call when
   the inputs are complete; it returns the four verdicts, the
   failing_checks list and overall_pass.
7. Confirm the deterministic anchors with the contract test
   scripts/test_ewis_installation_quality.py.

## Worked example

A 28 VDC EWIS run: 12 conductors of 2.0 mm diameter in a 12 mm conduit,
R = 0.008 ohm/m over 15 m, current 5 A, actual bend radius 8 mm,
separation from a hydraulic line 60 mm actual against 150 mm required.

Module outputs (scripts/ewis_installation_quality_logic.py):

- Wire area: wire_area(2.0) = 3.1416 mm2; bundle 37.699 mm2 against a
  conduit area of 113.097 mm2.
- Fill ratio: bundle_fill_ratio([2.0] * 12, 12.0) = 0.3333, fill_check
  margin = 0.40 - 0.3333 = +0.0667, PASS (0.333 <= 0.40).
- Round-trip resistance: round_trip_resistance(0.008, 15.0) = 0.24 ohm
  exactly (2 * 0.008 * 15).
- Voltage drop: drop_V = 5 * 0.24 = 1.2 V, drop_pct = 4.2857% of the
  28 V bus (assert 1e-9 relative), FAIL against the 2% limit, margin
  -2.2857 points.
- Bend radius: required = 6.0 * 2.0 = 12 mm, actual 8 mm, margin
  8/12 - 1 = -0.3333, FAIL.
- Separation: margin = 60/150 - 1 = -0.6, FAIL.

Verdict table from ewis_installation_report(28.0, [2.0] * 12, 12.0,
0.008, 15.0, 5.0, 8.0, 60.0, 150.0):

| Check | Value | Limit | Margin | Verdict |
|---|---|---|---|---|
| fill | 0.3333 | 0.40 | +0.0667 | PASS |
| voltage drop | 1.2 V, 4.2857% | 2.0% | -2.2857 | FAIL |
| bend radius | 8 mm | 12 mm | -0.3333 | FAIL |
| separation | 60 mm | 150 mm | -0.6 | FAIL |

overall_pass is False with failing_checks exactly
['voltage_drop', 'bend_radius', 'separation']: the drop, bend and
separation checks fail and the fill check passes.

## Verification

- Confirm bundle_fill_ratio([2.0] * 12, 12.0) returns 0.3333 (bound
  0.30 to 0.37) and that fill_check(0.40) passes (pass_bool is
  fill_ratio <= limit, so exactly at the limit is a pass).
- Confirm round_trip_resistance(0.008, 15.0) returns 0.24 exactly and
  voltage_drop(28.0, 5.0, 0.24) returns drop_V 1.2 V and drop_pct
  4.2857% (1e-9 relative).
- Confirm bend_radius_check(2.0, 8.0) gives required_radius 12.0 mm,
  margin -0.3333 and pass_bool False, and that 12 mm actual passes.
- Confirm separation_check(60.0, 150.0) gives margin -0.6 and
  pass_bool False, and that 150 mm actual passes with margin 0.
- Confirm ewis_installation_report on the worked example returns
  overall_pass False with exactly the three failing checks named above.
- Confirm ValueError rejection: conduit_diameter <= 0, an empty wire
  list, any wire diameter <= 0, voltage <= 0, current < 0, resistance
  < 0, actual_bend_radius < 0, factor <= 0, required_distance <= 0 and
  actual_distance < 0 all raise ValueError.
- Run the contract test offline: python3
  scripts/test_ewis_installation_quality.py (32 tests, deterministic).

## Related leaves

- manufacturing-quality/assembly/fastener-installation-quality: the
  sibling assembly leaf for structural fastener grip, clamp load and
  installation verdicts at the same acceptance step.
- manufacturing-quality/special-processes/special-process-qualification:
  change control when an EWIS wiring process itself changes and needs
  requalification; installation checks here assume a qualified process.
- avionics/data-bus/arinc664-afdx: the data bus signaling context that
  the EWIS physical layer carries; protocol design is out of scope for
  this leaf.

## Pitfalls

- Computing the voltage drop one-way: the run's resistance is
  round-trip (R_rt = 2 * R_per_m * L), so forgetting the return path
  halves the drop - the worked example drops 1.2 V / 4.2857% only
  because the 0.24 ohm round-trip value is used.
- Sizing the bend check against the average conductor: the largest
  single conductor in the bundle drives the required radius (worst
  case), so a bundle whose mean diameter passes can still fail on its
  biggest wire.
- Flagging a fill ratio exactly at the limit: all four checks pass on
  margin >= 0, so fill 0.40 against the 0.40 limit passes - only a
  fill above the limit fails.
- Mixing units across the inputs: the relations assume mm for
  diameters, radii and distances, m for run length, ohm/m for
  resistance, and V/A for the electrical inputs, so a cm conduit
  diameter silently corrupts the fill verdict.
- Reading overall_pass without the failing check list: the verdict
  aggregates four independent checks and names the failures
  (voltage_drop, bend_radius, separation in the worked example), so a
  bare pass/fail without the list hides which check needs rework.
- Treating this leaf as an EWIS design tool: it verifies the physical
  installation of a run under a qualified wiring process; routing and
  splice-layout design are out of scope, and a changed process itself
  routes to special-process-qualification.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ewis_installation_quality.py

The test covers the worked-example contract (fill 0.3333 within the
0.30 to 0.37 bound, exact 0.24 ohm round-trip resistance, drop 4.2857%
at 1e-9 relative, bend required 12 mm against 8 mm actual, separation
margin -0.6, and overall_pass False with exactly the three failing
checks), the fill boundary at exactly 0.40 passing, pass cases for all
four checks, custom fill, bend and drop limits, the round-trip and
area identities, and ValueError rejection of every non-physical input
in the validation list.

## Compliance

- Standards referenced, not reproduced: AS9100 is the aerospace quality
  management system standard that frames the manufacturing acceptance
  context; the check relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
