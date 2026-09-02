---
name: radio-frequency-susceptibility
description: "Use when you must plan and execute a DO-160 section 20 radio frequency susceptibility (RF immunity) test on airborne equipment: compute the radiated field strength from amplifier power, antenna gain, and distance; size the amplifier power budget for a required field level including cable loss and calibration margin; convert between V/m and dBuV/m, A and dBuA, and W and dBm; estimate the AM-modulated peak field and average power; and check conducted immunity margins against CS114 category current limits. Produces the field strength, the amplifier power budget, and the pass-fail margins that gate RF immunity test planning. Trigger: radio frequency susceptibility, RS103, CS114, radiated immunity, conducted immunity, field strength, RF test, amplifier power."
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
  tags: [radio-frequency-susceptibility, radiated-susceptibility, conducted-susceptibility, rf-immunity-testing, rs103, cs114, field-strength, amplifier-power-sizing, do-160-section-20, calibration-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-160 Radio Frequency Susceptibility (avionics/do160/radio-frequency-susceptibility)

Use when the task is RF immunity testing of airborne equipment per
DO-160 section 20: computing radiated field strength from the
amplifier and antenna setup, sizing the amplifier power budget with
cable loss and calibration margin, converting between the dB units of
the test levels, and judging conducted immunity margins against the
CS114 category current limits.

## Domain quick reference

- DO-160 section 20 (RTCA, EUROCAE twin ED-14G) covers radio frequency
  susceptibility: radiated immunity (RS101 magnetic field, RS103
  radiated field) and conducted immunity (CS101 audio frequency on
  power leads, CS114 bulk cable injection, CS115/CS116 transients).
  Section 21 covers the companion emission tests (RE102 radiated, CE102
  conducted).
- Far-field relation: E = sqrt(30 * P * G) / d, with E in V/m, P the
  radiated power in W, G the linear antenna gain, and d the distance in
  m. Inverting gives P = E^2 * d^2 / (30 * G), the power needed to
  produce a required field level.
- dB conventions: field level in dBuV/m is 20 * log10(E / 1e-6), with
  120 dBuV/m equal to 1 V/m; current in dBuA is 20 * log10(I / 1e-6),
  with 120 dBuA equal to 1 A; power in dBm is 10 * log10(P / 1e-3),
  with 30 dBm equal to 1 W.
- Power flux density: the plane-wave flux S = E^2 / 377 W/m2, with 377
  ohm the free-space impedance; E = sqrt(S * 377).
- Amplitude modulation: the RS103 modulated field peaks at E * (1 + m)
  and the average power is P * (1 + m^2 / 2), with m the modulation
  depth (typically 0.8).
- Calibration margin: raising the calibration level by M dB multiplies
  the field by 10^(M / 20) and the amplifier power by 10^(M / 10).
- CS114 categories: adjacent categories step the current limit by
  10 dBuA (A through H, then J; the letter I is skipped). Published
  category base levels are summary reference data, verify against the
  current DO-160 revision before test planning.
- RS103 radiated levels span roughly 1 to 200 V/m depending on
  equipment category, over bands extending up to 18 GHz; the exact
  category table must be verified against the current revision.
- Far field: the far-field relation holds beyond the Fraunhofer
  distance R = 2 * D^2 / lambda, with D the antenna aperture and
  lambda = c / f the wavelength; at 1 GHz the wavelength is 0.2998 m.

## Workflow

1. Confirm the DO-160 revision, the equipment category, and the
   applicable immunity tests (radiated RS103, conducted CS101/CS114,
   or both) from the qualification matrix.
2. Convert the required test level to SI: field in V/m via
   vm_from_dbu_vm, current in A via amp_from_dbu_a, power in W via
   watt_from_dbm.
3. Size the radiated setup: compute the amplifier power with
   power_for_field_strength from the field, antenna gain, and
   distance, then add cable loss with amplifier_power_with_cable_loss
   and the calibration margin with apply_margin_db, or use
   required_amp_power_for_test for the full budget in one call.
4. Confirm the setup is in the far field: check the test distance
   against far_field_boundary at the highest test frequency, using
   wavelength_from_frequency.
5. Estimate the modulated stress: am_peak_field for the instantaneous
   peak and am_average_power for the average amplifier load.
6. Judge conducted immunity: compare the measured injection current
   with the CS114 category limit via cs114_limit_dbu_a and
   margin_check_dbu, and record the margin and the pass-fail verdict.

## Pitfalls

- Mixing dB conventions: 20 log10 for field and current, 10 log10 for
  power; applying the power convention to a field level is wrong by a
  factor of 2 in dB.
- Using average power when the AM peak matters: the modulated field
  peaks at E * (1 + m), above the unmodulated calibration level, and
  the receiver desensitization follows the peak.
- Forgetting the 377 ohm impedance when converting between field and
  flux density.
- Applying the margin in the wrong domain: a 6 dB field margin is
  10^(6/20), about 2x the field, not 10^(6/10).
- Using the far-field relation in the near field: at distances below
  the Fraunhofer boundary R = 2 * D^2 / lambda the field is not
  plane-wave and the power estimate is invalid.
- Treating section 21 emission limits as immunity limits: emissions
  bound what the equipment radiates, susceptibility bounds what it
  withstands, and the two have different units and pass criteria.
- Confusing CS114 categories: the set steps A through H then J,
  skipping I, so a category J limit is 80 dBuA above category A, not
  90.
- Trusting published category tables without revision checks: DO-160
  category levels change between revisions; verify before freezing a
  test plan.

## Behavior contract (gate 3)

The immunity math is exercised by the gate 3 contract test:
scripts/test_radio_frequency_susceptibility.py against
scripts/radio_frequency_susceptibility_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_radio_frequency_susceptibility.py

## Compliance

- Standards referenced, not reproduced: DO-160 text is proprietary
  (RTCA); summary-only per standards-map.yaml and brief 06. The
  far-field relation, dB conventions, and AM power relations above are
  common RF engineering, and the CS114 category levels are marked as
  summary reference data to be verified against the current revision.
- compliance: STANDARDS-REF, gated: false.
