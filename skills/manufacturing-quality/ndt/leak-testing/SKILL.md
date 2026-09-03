---
name: leak-testing
description: "Use when you must plan and evaluate a leak test on a fuel tank, accumulator, valve, or sealed enclosure: compute the leak rate in scc per second from pressure decay or vacuum decay measurement, size the test time a gauge resolution needs to catch a target leak, convert a measured helium leak to the air equivalent and back, recommend the leak test method from required sensitivity and access, and disposition the part against the maximum allowable leak rate. Produces the leak rate, the method recommendation, and the accept, reject, or review verdict. Trigger: leak testing, pressure decay, vacuum decay, helium mass spectrometer, sniffer test, bubble test, leak rate, scc per second, helium to air conversion, gauge resolution, maximum allowable leak."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: ndt
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [leak-testing, pressure-decay, vacuum-decay, helium-mass-spectrometer, sniffer-test, bubble-test, leak-rate, helium-to-air-conversion, gauge-resolution, maximum-allowable-leak]
  version: 0.1.0
  author: Aero Agent Skills
---

# Leak Testing (manufacturing-quality/ndt/leak-testing)

Use when the task is leak testing an aerospace part or system: computing the
leak rate from a pressure decay or vacuum decay measurement, sizing the test
time a gauge resolution needs, converting a measured helium leak to the
equivalent air leak and back, translating an immersion bubble observation into
a leak rate, recommending the leak test method from the required sensitivity
and access, and dispositioning the part against the maximum allowable leak
rate. This leaf implements the leak-rate measurement math and the method
screening in pure Python, stdlib only. It pairs with
manufacturing-quality/ndt/ndt-method-selection for the broader NDT method
screening context (leak testing sits beyond the five volumetric and surface
methods that leaf screens), with manufacturing-quality/as9100/calibration-control
for gauge resolution, and with manufacturing-quality/as9100/risk-management
for the process risk context.

## Domain quick reference

- Leak rate unit: standard cubic centimeters per second (scc/s), the gas
  volume at standard temperature 293.15 K that passes the leak per second.
- Pressure and vacuum decay: q = V_cc * dP_atm / t * (STD_TEMP_K / temp_K),
  with V_cc = volume_L * 1000 and dP_atm = dP_bar * BAR_TO_ATM, BAR_TO_ATM =
  0.986923. Pressure decay watches the pressure fall in a sealed part; vacuum
  decay watches the pressure rise in an evacuated chamber. Same math.
- Gauge resolution time: invert the decay equation, t = V_cc * dP_atm /
  q_target, the test time that makes a target leak produce a pressure change
  above the gauge resolution.
- Helium to air conversion: q_air = q_he * sqrt(M_HE / M_AIR), with M_HE =
  4.003 and M_AIR = 28.97 g/mol, so the factor is sqrt(4.003 / 28.97) = 0.3717.
  This is the documented typical molecular flow relation; a viscous flow leak
  sits closer to the viscosity ratio, which the approved procedure resolves.
- Bubble (immersion): q = (4/3) * pi * (d/2)^3 * bubbles_per_s with d in cm,
  the per bubble volume times the bubble count.
- Method screening thresholds (typical values, module constants): helium mass
  spectrometer hood when the required sensitivity is at or below 1e-6 scc/s
  (MS_THRESHOLD); helium sniffer when localization is needed and the
  sensitivity is at or below 1e-5 scc/s (SNIFFER_THRESHOLD); pressure or
  vacuum decay when only one side is accessible and the part cannot be
  immersion tested; bubble when localization is needed and the sensitivity is
  at or below 1e-2 scc/s (BUBBLE_THRESHOLD); otherwise pressure decay. A
  helium mass spectrometer resolves leaks down to about 1e-9 scc/s He
  (HELIUM_MS_MIN_DETECT_SCCS).
- Disposition: accept when measured <= max allowable; reject when measured
  exceeds the allowable by a ratio above 1.25 (REVIEW_RATIO); review in the
  band between. margin_db = 10 * log10(max_allowable / measured), positive on
  accept, negative on reject.
- AS9100 frames the special process control context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Record the test: part internal volume in liters, pressure drop in bar and
   the test time, then compute the leak rate with pressure_decay_rate (or
   vacuum_decay_rate for an evacuated chamber, chamber_volume_L in liters).
   Both return scc/s at standard temperature.
2. Check the measurement is meaningful: gauge_resolution_time(volume_L,
   gauge_res_bar, target_sccs) gives the seconds needed for the target leak to
   show above the gauge resolution. If the planned test is shorter, extend it.
3. Convert units when the reading is helium based: helium_to_air(q_he_sccs)
   for the air-equivalent leak of a helium mass spectrometer reading,
   air_to_helium(q_air_sccs) to go the other way.
4. For an immersion bubble observation, convert the bubble stream to a leak
   rate with bubble_leak_rate(bubble_diameter_mm, bubbles_per_s).
5. Screen the method with method_recommendation(required_sensitivity_sccs,
   access_both_sides, need_localization, part_pressure_capable), which returns
   the method and the rationale from the deterministic threshold chain.
6. Disposition the part with disposition(measured_sccs, max_allowable_sccs,
   method) and read the verdict plus margin in dB, or use
   helium_ms_verdict(detected_sccs_he, limit_sccs_air) for a helium reading
   against an air limit.
7. For a one-call decay summary, summarize(volume_L, dP_bar, time_s,
   max_allowable_sccs, method) returns the leak rate, method, verdict and
   margin in one dict.
8. Confirm the deterministic checks with the contract test
   scripts/test_leak_testing.py.

## Worked example

A 50 L fuel tank is pressure decay tested: 0.02 bar drop in 600 s.

- Leak rate: q = 50000 cc * 0.019738 atm / 600 = 1.645 scc/s
  (pressure_decay_rate(50, 0.02, 600), module value 1.644872). Against a
  2 scc/s maximum allowable the disposition is accept with margin
  10 * log10(2 / 1.645) = 0.849 dB.
- Gauge check: with a 0.001 bar gauge resolution and a 0.05 scc/s target
  leak, gauge_resolution_time(50, 0.001, 0.05) = 986.9 s (module value
  986.923), so a 600 s test cannot catch a 0.05 scc/s leak.
- Helium conversion: a helium mass spectrometer reading of 1.0 scc/s He is
  0.3717 scc/s air (helium_to_air), so a detected 1e-8 scc/s He leak is
  3.7e-9 scc/s air equivalent, accept against a 1e-8 scc/s air limit
  (helium_ms_verdict).
- Bubble: a 3 mm bubble at 1 per second is (4/3) * pi * (0.15 cm)^3 =
  0.01414 scc/s (bubble_leak_rate(3.0, 1.0), module value 0.014137).
- Method screening: a sealed valve needing 1e-8 scc/s sensitivity routes to
  the helium mass spectrometer hood; a part with 1e-4 scc/s sensitivity that
  needs localization and has both sides accessible routes to bubble
  immersion; a one-sided part that holds pressure routes to pressure decay.
- Disposition bands: 1.0 vs 2.0 scc/s accept with 3.01 dB margin; 3.0 vs
  2.0 reject (ratio 1.5 above 1.25); 2.4 vs 2.0 review (ratio 1.2 in the
  band).

## Verification

- Confirm pressure_decay_rate(50, 0.02, 600) returns 1.644872 scc/s, within
  rounding of the 1.645 scc/s anchor, and equals the direct formula
  V_cc * dP_atm / t at standard temperature.
- Confirm gauge_resolution_time(50, 0.001, 0.05) returns 986.923 s, within
  rounding of the 986.9 s anchor, and that doubling the target halves the
  time.
- Confirm helium_to_air(1.0) equals sqrt(4.003 / 28.97) = 0.371722 and that
  air_to_helium(helium_to_air(x)) recovers x within 1e-12.
- Confirm bubble_leak_rate(3.0, 1.0) equals (4/3) * pi * 0.15^3 = 0.014137
  scc/s.
- Confirm method_recommendation picks the helium mass spectrometer hood at
  1e-8 scc/s, the helium sniffer at 1e-5 with localization, and bubble at
  1e-4 with localization and both sides accessible.
- Confirm disposition margins: accept at 1.0 vs 2.0 with margin 3.01 dB,
  reject at 3.0 vs 2.0, review at 2.4 vs 2.0.
- Confirm every non-positive volume, time, temperature, target, allowable,
  every negative pressure drop, and every unknown method string raises
  ValueError.
- Run the contract test offline: python3 scripts/test_leak_testing.py
  (34 tests, deterministic).

## Related leaves

- manufacturing-quality/ndt/ndt-method-selection: the RT, UT, ET, PT and MT
  screening context that stops short of leak testing.
- manufacturing-quality/as9100/calibration-control: gauge resolution and
  calibration control for the test instrumentation.
- manufacturing-quality/as9100/risk-management: process risk context for the
  leak test acceptance decisions.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_leak_testing.py

The test covers the pressure and vacuum decay worked example (50 L, 0.02 bar,
600 s to 1.645 scc/s), the gauge resolution time anchor (986.9 s), the helium
to air conversion and both round trips, the bubble geometry anchor (3 mm at
1 bubble/s to 0.01414 scc/s), every method recommendation branch of the
threshold chain, the disposition accept, reject and review bands including
the 1.25 ratio edges, the helium mass spectrometer verdict, the summarize
dict, and ValueError rejection of all non-physical inputs.

## Compliance

- Standards referenced, not reproduced: AS9100 is named as the special
  process control frame by id only, per standards-map.yaml; all relations
  above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
