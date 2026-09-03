# Wave-30 leaf spec: ewis-installation-quality (manufacturing-quality, assembly pack)

- Path: skills/manufacturing-quality/assembly/ewis-installation-quality/
- Pack: assembly (sibling: fastener-installation-quality only).
- Standards ids: as9100 (reference-only; MQ assembly convention). Ledger
  Standard: as9100.
- Family: manufacturing-quality

## Claim

Verify the installation quality of an electrical wiring interconnection system
(EWIS) installation during aerospace assembly: compute the conductor bundle
fill ratio against a conduit or clamp cross-section and check it against the
fill limit, compute the round-trip voltage drop of a conductor run and its
percent of the nominal bus voltage against a drop limit, check the bend radius
of a conductor against the minimum radius factor, and check the separation
distance between an EWIS bundle and a nearby fluid line or structure against
the required clearance. Produces the fill ratio, voltage drop, bend-radius and
separation verdicts that gate an EWIS installation acceptance.

Does NOT do: verify structural fastener installation (fastener-installation-
quality owns grip length, thread protrusion, torque); select NDT methods or
inspect terminations (manufacturing-quality ndt leaves own inspection);
design avionics data buses or encode bus protocols (avionics data-bus leaves
own ARINC 429, ARINC 664, MIL-STD-1553 signaling); qualify wire harness
processes under a special-process change (special-process-qualification owns
change classification). EWIS physical installation checks only: geometry,
fill, drop, bend, and separation; the wire gauge, resistance per meter, and
current are inputs.

## Model (implement exactly)

Module constants:
- FILL_LIMIT = 0.40 (typical maximum bundle fill ratio for a new install).
- BEND_FACTOR_DEFAULT = 6.0 (minimum bend radius as a multiple of the
  conductor diameter for a shielded/wire bundle install).
- VOLTAGE_DROP_LIMIT_PCT = 2.0 (percent of nominal bus voltage, default
  acceptance limit).
- PI = math.pi.

Functions (pure stdlib):
- wire_area(diameter) -> PI * (diameter/2)**2.
- bundle_fill_ratio(wire_diameters, conduit_diameter) -> float:
  sum(wire areas) / conduit area. ValueError if conduit_diameter <= 0 or any
  wire diameter <= 0 or empty list.
- fill_check(fill_ratio, limit=FILL_LIMIT) -> dict: {fill_ratio, limit,
  pass_bool, margin (limit - fill_ratio)}.
- round_trip_resistance(resistance_per_meter, length_m) -> 2 * R_per_m * L.
- voltage_drop(voltage, current_A, resistance_ohms) -> dict: {drop_V,
  drop_pct} with drop_V = current * resistance (round trip already included in
  the caller's resistance), drop_pct = 100 * drop_V / voltage. ValueError if
  voltage <= 0, current < 0, resistance < 0.
- bend_radius_check(conductor_diameter, actual_bend_radius,
  factor=BEND_FACTOR_DEFAULT) -> dict: {required_radius, actual_radius,
  pass_bool, margin (actual_radius / required_radius - 1)}. ValueError if
  conductor_diameter <= 0, actual_bend_radius < 0, factor <= 0.
- separation_check(actual_distance, required_distance) -> dict: {pass_bool,
  margin (actual / required - 1)}. ValueError if required_distance <= 0 or
  actual_distance < 0.
- ewis_installation_report(voltage, wire_diameters, conduit_diameter,
  resistance_per_meter, length_m, current_A, actual_bend_radius,
  bend_factor=BEND_FACTOR_DEFAULT, separation_actual, separation_required,
  fill_limit=FILL_LIMIT, drop_limit_pct=VOLTAGE_DROP_LIMIT_PCT) -> dict:
  aggregates fill_check, voltage_drop, bend_radius_check, separation_check
  plus {overall_pass} (all four pass_bool true). ValueErrors propagate.

## Worked example

28 VDC bus: 12 conductors of 2.0 mm diameter in a 12 mm conduit, R = 0.008
ohm/m, run length 15 m, current 5 A, actual bend radius 8 mm, separation from
a hydraulic line 60 mm actual vs 150 mm required.

Deterministic anchors (module outputs as assert targets; bounds):
- wire area each = pi = 3.14159 mm2; bundle area 37.699 mm2; conduit area
  113.097 mm2; fill ratio = 0.3333 (bound 0.30-0.37) -> PASS (0.333 < 0.40).
- round-trip resistance = 2 * 0.008 * 15 = 0.24 ohm (EXACT).
- voltage drop = 5 * 0.24 = 1.2 V; drop pct = 4.2857% (EXACT 1.2/28*100 =
  4.285714; assert 1e-9 relative) -> FAIL vs 2% limit (margin negative).
- bend radius: required = 6 * 2.0 = 12 mm; actual 8 mm -> FAIL; margin
  8/12 - 1 = -0.3333.
- separation: margin = 60/150 - 1 = -0.6 -> FAIL.
- overall_pass False with exactly the three failing checks named.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example (a small verdict table is ideal).

## Validation list (contract test must include)

- ValueError: conduit_diameter <= 0, empty wire list, any wire <= 0,
  voltage <= 0, current < 0, resistance < 0, actual_bend_radius < 0,
  factor <= 0, required_distance <= 0, actual_distance < 0.
- Pass/fail boundary: fill exactly at 0.40 passes (>= comparison with limit
  is fail; == limit passes: pass_bool = fill_ratio <= limit).
- Exact anchors above.
- Determinism.

## Corpus fragment (eval/hit1-wave30-ewis-installation-quality.yaml)

Forbidden tokens (siblings/other leaves): grip-length, torque, fastener
(fastener-installation-quality); arinc, databus, protocol (avionics);
termination-crimp, ultrasonic (ndt). Distinctive tokens ONLY:
ewis-installation, wiring-harness, bundle-fill-ratio, voltage-drop-check,
bend-radius-check, separation-clearance.

Query 1: "Verify an ewis-installation wiring-harness: bundle-fill-ratio of 12
x 2 mm conductors in a 12 mm conduit and the bend-radius-check at 8 mm"
(id w30-ewis-installation-quality-1).
Query 2: "Check the voltage-drop-check of a 28 VDC EWIS run at 15 m and the
separation-clearance from a hydraulic line" (id w30-ewis-installation-quality-2).
intent: "manufacturing-quality; EWIS installation acceptance checks".

## Description/tag guidance

Description opens "Use when you must verify the installation quality of an
electrical wiring interconnection system (EWIS) installation during aerospace
assembly:" and lists the outputs in the Claim. First tag:
ewis-installation-quality. Additional tags: wiring-harness,
bundle-fill-ratio, voltage-drop-check, bend-radius-check,
separation-clearance. No generic single words. 50-150 words, <=1000 chars, no
em dash, no "classified".
