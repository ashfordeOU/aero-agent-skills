---
name: electrostatic-discharge
description: "Determine DO-160 Section 25 electrostatic discharge (ESD) test parameters for airborne equipment: select the single equipment category and 15 kV air discharge test level, compute the stored energy and discharge waveform currents (peak, 30 ns, 60 ns) from the 150 pF and 330 ohm generator model, check the 10 positive and 10 negative discharges per test point, and judge test point applicability from personnel accessibility with connector pins excluded. Use when planning or auditing ESD qualification of LRUs and cabin equipment that personnel handle during normal operation or maintenance. Verdict logic classifies pass criteria; input validation and summary formulas only, no standard tables reproduced. Trigger: electrostatic discharge, ESD testing, air discharge, discharge waveform, test point."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-160
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do160
  tags: [electrostatic-discharge, esd-testing, air-discharge, discharge-waveform, test-levels, personnel-access, connector-pins, generator-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# Electrostatic Discharge (avionics/do160/electrostatic-discharge)

Use when the task is DO-160 Section 25 electrostatic discharge (ESD)
testing: selecting the equipment category and air discharge test
level, computing stored energy and discharge waveform currents from
the generator model, checking the discharge count per test point, and
judging whether a surface is an applicable test point for personnel
accessibility.

## Domain quick reference

- DO-160G (RTCA, EUROCAE twin ED-14G) section 25 covers immunity of
  equipment to electrostatic discharge from personnel handling.
- There is a single equipment category, A, tested at 15 kV air
  discharge on the equipment bonded to the ground plane. Worked: the
  category test level function returns 15.0 kV for category A and
  rejects any other category.
- The discharge generator follows the IEC 61000-4-2 human-body model:
  150 pF storage capacitance and 330 ohm discharge resistance.
- Stored energy: E = 0.5 * C * V^2. Worked: 150 pF at 15 kV gives
  0.5 * 150e-12 * (15e3)^2 = 0.016875 J (16.9 mJ); at 8 kV it gives
  4.8 mJ. Energy scales with the square of the test voltage.
- First peak current: 3.75 A/kV. Worked: 15 kV gives 56.25 A; 2 kV
  gives 7.5 A.
- Current at 30 ns: 2 A/kV. Worked: 15 kV gives 30 A. Current at
  60 ns: 1 A/kV. Worked: 15 kV gives 15 A.
- Rise time window: 0.7 to 1.0 ns. Worked: 0.8 ns is valid; 0.5 ns
  and 1.2 ns are outside the window.
- RC time constant: tau = R * C. Worked: 330 ohm and 150 pF give
  330 * 150e-12 = 49.5 ns.
- Discharges per test point: 10 positive and 10 negative, at the
  selected level. Worked: 10 and 10 is a valid plan; 9 and 10 is not.
- Test points: surfaces accessible to personnel during normal
  operation or during maintenance. Connector pins are not applicable
  test points (DO-160G).
- Pass criteria: equipment operates as specified during and after the
  discharges with no permanent degradation of performance.
- The actual level and waveform tables are standard data; read them
  from the current revision of DO-160. This skill is selection and
  verdict logic only, no standard tables reproduced.

## Workflow

1. Confirm the applicable DO-160 revision and equipment installation.
2. Confirm the equipment category with category_test_level_kv and read
   the test level (15 kV air discharge for category A).
3. Compute stored energy with stored_energy_joules.
4. Compute the discharge waveform currents with peak_current_amps,
   current_at_30ns_amps, and current_at_60ns_amps.
5. Check the rise time with rise_time_valid_ns and the network time
   constant with rc_time_constant_ns.
6. Check the discharge plan with discharge_count_valid (10 positive,
   10 negative per test point).
7. Judge each candidate surface with test_point_applicable.
8. Classify the result with pass_verdict.

## Pitfalls

- Confusing section 25 ESD with section 22 lightning induced
  transients (avionics/do160/lightning-protection): ESD uses a 150 pF
  / 330 ohm air discharge generator at 15 kV, while lightning uses
  level and waveform set tables on induced transients; do not reuse
  lightning levels for ESD.
- Confusing ESD with power input testing (avionics/do160/power-input):
  section 16 covers bus voltage limits, sag and surge transients, and
  frequency tolerance; ESD discharges are applied to accessible
  surfaces, not to the power pins.
- Treating ESD as part of the environmental test matrix
  (avionics/do160/environmental-qualification): section 25 is a
  standalone EMC section with its own applicability rule (personnel
  accessibility), not a category letter in the temperature or
  vibration tables.
- Testing connector pins: DO-160G excludes connector pins as ESD test
  points; a surface that is a connector pin is not applicable even
  when accessible.
- Using fewer than 10 discharges per polarity: the plan must include
  at least 10 positive and 10 negative discharges per test point.
- Applying contact discharge levels from IEC 61000-4-2 without
  checking the DO-160 category: DO-160 section 25 specifies the air
  discharge test at 15 kV for category A.
- Using a generator model other than 150 pF and 330 ohm: automotive
  models (for example 330 pF) do not match the DO-160 human-body
  model and change the stored energy and waveform currents.
- Judging pass on operation alone: the verdict requires both
  operation as specified and no permanent degradation of performance.

## Behavior contract (gate 3)

The selection and verdict logic is exercised by the gate 3 contract
test: scripts/test_electrostatic_discharge.py against
scripts/electrostatic_discharge_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_electrostatic_discharge.py

## Compliance

- Standards referenced, not reproduced: DO-160 text is proprietary
  (RTCA); summary-only per standards-map.yaml and brief 06.
- The level, waveform, and discharge count tables are standard data;
  read them from the current revision before use.
- compliance: STANDARDS-REF, gated: false.
