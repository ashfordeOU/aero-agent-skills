---
name: electrical-wire-sizing
description: "Use when you must size an aircraft electrical wire run: select the smallest conductor gauge whose bundled ampacity at the ambient temperature meets the continuous load with the bundle and temperature derating applied, check the round-trip voltage drop over the run length at the load current against the bus tolerance, compute the percentage drop, and report the selected gauge, its ampacity margin, the voltage drop and the percent-drop verdict. Produces the conductor gauge selection and the drop verdict that close the load-to-distribution chain. Trigger: power feeder gauge selection, conductor ampacity, ampacity derating, wire voltage drop, percent drop, bus tolerance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [electrical-wire-sizing, conductor-ampacity, wire-voltage-drop, bus-tolerance-verdict, ewis-conductor-selection, ampacity-derating]
  version: 0.1.0
  author: AeroSkills
---

# Electrical Wire Sizing (vehicle-design/sizing/electrical-wire-sizing)

Use when you must size an aircraft electrical wire run at the feeder
level: converting a continuous load current, ambient temperature,
conductor temperature and run length into a gauge selection by derated
bundled ampacity, then checking the round-trip voltage drop at the load
current against the bus tolerance. This leaf implements the standard
conductor ampacity derating and resistance model in pure Python (stdlib
only), over a documented copper conductor reference data set for gauges
22 AWG down to 6 AWG. It pairs with
vehicle-design/sizing/aircraft-electrical-load-analysis, which builds
the per-bus consumer load rollup that supplies the continuous load used
here, and with vehicle-design/sizing/battery-sizing, whose pack circuit
drop check is not a wire run sizing. Does NOT do: EWIS installation and
inspection quality (manufacturing-quality/assembly/ewis-installation-
quality); avionics thermal management (vehicle-design/sizing/avionics-
bay-cooling-sizing).

## Domain quick reference

- Ampacity model: A(gauge, T_amb) = A_base * BUNDLE_DERATE *
  TEMP_DERATE(T_amb), with A_base the free-air 30 C base ampacity from
  the module constant set (5.0 A at 22 AWG rising to 60.0 A at 6 AWG),
  BUNDLE_DERATE = 0.60 for a bundle of 5 or more wires, and the linear
  temperature derate 1.0 - 0.006 * (T_amb - 30), floored at 0.5.
- Temperature derate values: 1.0 at 30 C, 0.94 at 40 C, 0.91 at 45 C.
  The 0.94 module constant is the documented value at the 40 C
  calibration point of the linear slope; the worked example runs at
  45 C with the 0.91 factor as anchored.
- Selection rule: the smallest gauge whose derated ampacity meets the
  continuous load is selected; the model covers 22 AWG up to 6 AWG and
  raises ValueError when the load exceeds the 6 AWG derated capacity.
- Resistance model: R = rho * (1 + alpha * (T - 20)) / A_x, with
  rho = 1.72e-8 ohm m at 20 C for copper, alpha = 0.00393 per C, and
  A_x the conductor cross section in m^2 from the area constant set.
  At 45 C, 8 AWG gives 2.257e-3 ohm/m and 6 AWG gives 1.420e-3 ohm/m.
- Voltage drop (round trip): V_drop = 2 * L * I * R, then the percent
  drop is 100 * V_drop / V_bus; the run passes when the percent drop is
  at or below MAX_PERCENT_DROP = 3.0 percent of the bus voltage.
- SAE AS50881 frames the EWIS derating context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the run inputs: continuous load current I, run length L, bus
   voltage V_bus, ambient temperature T_amb, conductor temperature T_c.
2. Check candidate ampacities at the ambient with ampacity(gauge,
   T_amb); at 45 C the derate multiplies the free-air base by 0.60 *
   0.91, which is the 0.546 effective factor.
3. Select the conductor with select_gauge(I, T_amb), the smallest gauge
   whose derated ampacity meets the load.
4. Get the conductor resistance at the operating temperature with
   resistance_per_meter(gauge, T_c).
5. Compute the round-trip drop with voltage_drop(I, L, gauge, T_c) and
   its percentage of the bus with percent_drop(V_drop, V_bus).
6. Run the full bundle with wire_size_review(I, L, V_bus, T_amb, T_c),
   which returns the selected gauge, ampacity, margin, drop, percent
   drop and the pass or fail verdict against the 3 percent bus
   tolerance.
7. When the verdict is fail, upsize one gauge and re-check the drop
   with the primitive functions until the percent drop clears the bus
   tolerance.
8. Confirm the deterministic checks with the contract test
   scripts/test_electrical_wire_sizing.py.

## Worked example

A 25 A continuous load on a 10 m run fed from a 28 V DC bus, ambient
45 C and conductor temperature 45 C.

- Derated ampacity check: ampacity("10", 45.0) = 18.018 A, below the
  25 A load; ampacity("8", 45.0) = 25.116 A meets it, so
  select_gauge(25.0, 45.0) = "8".
- Resistance: resistance_per_meter("8", 45.0) = 2.257e-3 ohm/m.
- Drop on 8 AWG: voltage_drop(25.0, 10.0, "8", 45.0) = 1.128 V, which
  is percent_drop = 4.03 percent of the 28 V bus, above the 3.0 percent
  tolerance, verdict fail.
- Upsize to 6 AWG: ampacity("6", 45.0) = 32.76 A, resistance
  1.420e-3 ohm/m, voltage_drop(25.0, 10.0, "6", 45.0) = 0.710 V,
  percent 2.54 percent, verdict pass. Final selection 6 AWG.
- Review bundle: wire_size_review(25.0, 10.0, 28.0, 45.0, 45.0)
  returns gauge "8", ampacity 25.116 A, margin 0.116 A, drop 1.128 V,
  percent 4.03, verdict "fail", which flags the drop-limited upsize to
  6 AWG above. Over a short 2 m run the same 8 AWG selection drops
  0.806 percent and passes.

## Verification

- Confirm select_gauge(25.0, 45.0) returns "8" and
  select_gauge(5.0, 30.0) returns "18" (the truth table smallest gauge
  meeting the load).
- Confirm the 45 C ampacity anchors: 18.018 A at 10 AWG, 25.116 A at
  8 AWG, 32.76 A at 6 AWG (bounds 18.0 / 25.1 / 32.8 A within 0.2 A).
- Confirm resistance_per_meter("8", 45.0) = 2.257e-3 ohm/m within 5
  percent and the 6 AWG value 1.420e-3 ohm/m.
- Confirm the drop anchors: 1.128 V on 8 AWG and 0.710 V on 6 AWG
  within 0.05 V, with percent drops 4.03 and 2.54.
- Confirm the identities: doubling the run length doubles the drop, and
  percent_drop equals 100 * V_drop / V_bus exactly.
- Confirm every non-physical input raises ValueError: unknown gauge,
  load at or below zero or beyond the 6 AWG capacity, negative length,
  bus voltage at or below zero, ambient outside the 30 to 100 C band.
- Confirm determinism: repeated review calls return identical dicts
  with exactly the documented keys.
- Run the contract test offline: python3
  scripts/test_electrical_wire_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/aircraft-electrical-load-analysis: the per-bus
  consumer load rollup that supplies the continuous load current to the
  conductor sizing here.
- vehicle-design/sizing/battery-sizing: traction energy storage with
  pack cell count and an internal pack circuit drop check, not a wire
  run sizing.
- vehicle-design/sizing/avionics-bay-cooling-sizing: the thermal
  management side of the avionics installation.
- manufacturing-quality/assembly/ewis-installation-quality: EWIS
  installation and inspection quality, downstream of the gauge choice.

## Pitfalls

- Sizing on the undated free-air table: the base ampacity of 10 AWG is
  33 A free air, but in a 5+ wire bundle at 45 C the derated value is
  18.0 A, so an undated selection under-sizes the feeder.
- Using one-way resistance as one-way drop: the drop must cover the
  round trip, so the 2 * L factor applies; a 1.128 V drop is the two
  conductor total, not the one-way value.
- Stopping at the gauge that meets ampacity: in the worked example
  8 AWG meets the 25 A load but its 4.03 percent drop fails the 3
  percent bus tolerance, so the drop verdict drives the upsize to
  6 AWG.
- Reading the review verdict as the final selection: wire_size_review
  reports the ampacity-selected gauge with its drop verdict; a fail
  verdict means iterate the primitive functions one gauge up.
- Ignoring the ambient band: the model derate is defined for 30 to
  100 C ambient and raises ValueError outside it; derating below 30 C
  ambient is not part of this model.
- Confusing neighbors: the load rollup leaf, the battery pack leaf and
  the EWIS install quality leaf each own adjacent questions, and none
  of them selects a wire run gauge by derated ampacity.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_electrical_wire_sizing.py

The test covers the sizing contract: the 45 C ampacity anchors (18.0 /
25.1 / 32.8 A bounds at 10 / 8 / 6 AWG), the select_gauge truth table
and the beyond-table rejection, resistance anchors for 8 and 6 AWG at
45 C with the temperature ratio identity, the voltage-drop anchors
1.128 V and 0.710 V, the length-doubling and percent-drop identities,
the wire_size_review dict key contract with the fail and pass verdicts,
determinism, and ValueError rejection of unknown gauge, non-positive
load, negative length, non-positive bus voltage and out-of-band
ambient.

## Compliance

- Standards referenced, not reproduced: FAR 25 Subpart H frames the EWIS
  certification context and SAE AS50881 is named as the derating
  reference only; the ampacity derating and resistance relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
