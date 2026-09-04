---
name: radio-frequency-emissions
description: "Use when you must plan and check the DO-160 section 21 radio frequency emission test of airborne equipment: convert the measured conducted emission amplitude from volts to dBuV and the radiated emission field to dBuV/m at the antenna, classify the equipment installation category, apply the CE102 conducted emission limit curve and the RE102 radiated emission limit curve for the category, compute the emission margin at each frequency, find the worst case frequency, and judge the equipment pass or fail for the EMC qualification. Produces the emission margin, the worst case frequency, and the pass or fail verdict that gate the DO-160 EMC qualification. Trigger: radio frequency emissions, DO-160 section 21, conducted emissions, radiated emissions, CE102, RE102, emission limit, emission margin, dBuV, dBuV/m, EMC qualification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-160
    reference-only: true
gated: false
domain: avionics
pack: do160
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do160
  tags: [radio-frequency-emissions, do-160-section-21, conducted-emissions, radiated-emissions, ce102, re102, emission-limit, emission-margin, dbu-v-conversion, dbu-v-per-m-conversion, emc-qualification]
  version: 0.1.0
  author: AeroSkills
---

# Radio Frequency Emissions (avionics/do160/radio-frequency-emissions)

Use when the task is planning and checking the DO-160 section 21
equipment emission test of airborne equipment: CE102 conducted
emissions over 10 kHz to 10 MHz and RE102 radiated emissions over
2 MHz to 18 GHz. This leaf converts measured amplitudes into the dBuV
and dBuV/m scales, applies the reference-only typical limit model for
the installation category, computes the emission margin at every
frequency, finds the worst case frequency, and returns the pass or fail
verdict that gates the EMC qualification. It is implemented in pure
Python, stdlib only. The immunity counterpart (DO-160 section 20, the
radio-frequency-susceptibility leaf) owns the radiated and conducted
susceptibility tests of the same equipment; this leaf is strictly the
emission side, section 21.

## Domain quick reference

- Conducted emission level: dBuV = 20 * log10(V_uV), with V_uV the
  measured amplitude in uV (volts * 1e6). Anchors: 1 V is 120 dBuV,
  1 mV is 60 dBuV, 1 uV is 0 dBuV. dbu_v_from_volts and
  volts_from_dbu_v convert both ways.
- Radiated emission level: dBuV/m = 20 * log10(E_uV/m), with E in V/m.
  Anchor: 1 V/m is 120 dBuV/m. dbu_v_per_m_from_v_per_m converts one
  way; the RE102 antenna measurement is then expressed in dBuV/m.
- CE102 limit (reference-only typical, NOT the normative RTCA curve):
  piecewise constant over the test band, 78 dBuV below 100 kHz,
  60 dBuV from 100 kHz to 2 MHz, 70 dBuV from 2 MHz to 10 MHz. The
  normative conducted emission limit comes from the current DO-160
  revision. ce102_limit_db(freq_hz, category) applies the curve; the
  category is validated and carried through but does not shift this
  simplified model.
- RE102 limit (reference-only typical floors): category A 24 dBuV/m,
  category B 34 dBuV/m, category C 44 dBuV/m across 2 MHz to 18 GHz.
  The normative radiated emission curve varies within the band and must
  be read from the current DO-160 revision. re102_limit_db(freq_hz,
  category) applies the floor.
- Emission margin: margin_db = limit_db - measured_db at each
  frequency; a negative margin is a fail. conducted_emission_margin and
  radiated_emission_margin evaluate it on the dBuV and dBuV/m scales.
- Worst case: the frequency carrying the minimum margin across the
  sweep, returned by worst_case_frequency(freqs, margins).
- Verdict: pass when the minimum margin is >= 0 dB, returned by
  emission_verdict(margins, freq_hz, category, kind) as a dict with the
  pass flag, worst margin, worst frequency, and category. A margin band
  of >= 6 dB is a typical engineering recommendation, reference-only,
  not a hard RTCA requirement.
- Source sanity check: E (V/m) = sqrt(30 * P_erp) / d for a
  characterized radiating source, the inverse-square far-field
  relation. field_strength_from_erp returns V/m; convert with
  dbu_v_per_m_from_v_per_m to compare against RE102. This checks the
  emission source level, it does not size an immunity amplifier.
- Units: voltage in V, field in V/m, frequency in Hz, ERP in W,
  distance in m, levels in dBuV and dBuV/m.

## Workflow

1. Classify the equipment: pick the installation category (A, B, or C
   in this reference-only model) and the emission side under check,
   CE102 conducted or RE102 radiated.
2. Convert the measured amplitude: dbu_v_from_volts for a conducted
   measurement in volts, dbu_v_per_m_from_v_per_m for a radiated field
   measurement in V/m, so every measurement is on the dB scale of its
   limit curve.
3. Apply the limit at each measured frequency with ce102_limit_db or
   re102_limit_db for the category.
4. Compute the emission margin per point with conducted_emission_margin
   or radiated_emission_margin (limit minus measured).
5. Find the worst case frequency with worst_case_frequency over the
   sweep.
6. Judge the equipment with emission_verdict(margins, freq_hz,
   category, kind), where kind is conducted/CE102 or radiated/RE102.
7. When an antenna is characterized, sanity-check the radiating source
   level with field_strength_from_erp before blaming the equipment.
8. Confirm the deterministic checks with the contract test
   scripts/test_radio_frequency_emissions.py.

## Worked example

Category A equipment, representative measurements.

- Conducted: 72 dBuV measured at 150 kHz. The reference CE102 curve
  gives 60 dBuV at 150 kHz, so the margin is 60 - 72 = -12 dB, a fail.
- Radiated: 40 dBuV/m measured at 100 MHz. The RE102 category A floor
  is 24 dBuV/m, so the margin is 24 - 40 = -16 dB, a fail.
- Conducted sweep verdict: measured 60, 72, 68 dBuV at 50 kHz,
  150 kHz, and 5 MHz against the CE102 curve 78, 60, 70 dBuV gives
  margins +18, -12, +2 dB. worst_case_frequency returns 150 kHz at
  -12 dB and emission_verdict returns pass False with worst margin
  -12 dB at 150 kHz.
- Radiated sweep verdict: measured 15, 40, 20 dBuV/m at 10 MHz,
  100 MHz, and 1 GHz against the 24 dBuV/m floor gives margins +9,
  -16, +4 dB. emission_verdict returns pass False with worst margin
  -16 dB at 100 MHz.
- Source sanity check: 100 W ERP at 10 m gives
  E = sqrt(30 * 100) / 10 = 5.477 V/m, which is 134.77 dBuV/m at the
  antenna, far above any category floor, so the source itself must be
  screened or relocated before retesting the equipment.

## Verification

- Confirm dbu_v_from_volts(1.0) returns 120 dBuV and
  volts_from_dbu_v(120.0) returns 1 V (round trip holds).
- Confirm dbu_v_per_m_from_v_per_m(1.0) returns 120 dBuV/m.
- Confirm ce102_limit_db(150e3, "A") returns 60 dBuV and
  re102_limit_db(100e6, "A") returns 24 dBuV/m.
- Confirm conducted_emission_margin(72.0, 60.0) returns -12 dB and
  radiated_emission_margin(40.0, 24.0) returns -16 dB, and that
  emission_verdict over those sweeps reports fail with the worst case
  at the minimum margin frequency.
- Confirm every negative or zero amplitude, every non-positive
  frequency, every frequency outside the CE102 or RE102 test band,
  every unsupported category, every unknown kind, and every empty or
  mismatched sweep raises ValueError.
- Run the contract test offline: python3
  scripts/test_radio_frequency_emissions.py (32 tests, deterministic).

## Related leaves

- avionics/do160/radio-frequency-susceptibility: the DO-160 section 20
  counterpart that owns the radiated and conducted susceptibility
  tests of the same equipment (section 21 here is the emission side).
- avionics/do160/electrostatic-discharge: DO-160 section 25 ESD test
  levels and waveforms, another equipment-level EMC environment.
- avionics/do160/lightning-protection: DO-160 sections 22 and 23
  lightning induced transient and direct effects environments.

## Pitfalls

- Mixing linear and dB scales: every measurement must be converted to
  its dB domain first (dbu_v_from_volts with volts * 1e6 for conducted,
  dbu_v_per_m_from_v_per_m for radiated); feeding volts straight into a
  dBuV limit comparison misplaces the anchor by 120 dB at 1 V.
- Flipping the margin sign: margin is limit minus measured, so a
  negative margin is a fail - computing measured minus limit inverts
  the pass/fail verdict for every sweep point.
- Applying the wrong curve side: CE102 conducted limits and RE102
  radiated category floors are different functions of frequency, and
  emission_verdict needs the matching kind (conducted/CE102 or
  radiated/RE102); a radiated measurement checked against the CE102
  curve is meaningless.
- Quoting the simplified curves as normative limits: the CE102 band
  curve and the RE102 category A/B/C floors here are reference-only
  typical values, not the current RTCA/DO-160 section 21 table - the
  real curve varies within the band and must be read from the current
  revision before any qualification call.
- Misapplying the ERP sanity check: field_strength_from_erp checks the
  radiating source with the inverse-square far-field relation (100 W ERP
  at 10 m is 134.77 dBuV/m) - it does not size an immunity amplifier;
  amplifier sizing belongs to the radio-frequency-susceptibility leaf.
- Demanding a hard 6 dB band: the >= 6 dB margin band is a typical
  engineering recommendation, not an RTCA requirement; the verdict in
  this leaf passes at a minimum margin of >= 0 dB, so treat 6 dB as
  design guidance, not a failure criterion.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_radio_frequency_emissions.py

The test covers the dBuV and dBuV/m conversions and their anchors, the
reference-only typical CE102 band curve and RE102 category floors
including band edges, the worked example margins (-12 dB conducted at
150 kHz, -16 dB radiated at 100 MHz, category A), pass and fail
verdicts over single points and sweeps, worst case frequency selection
with tie handling, the ERP far-field sanity check with inverse-square
scaling, and ValueError rejection of non-physical inputs, out-of-band
frequencies, unsupported categories, unknown kinds, and empty or
mismatched sweeps.

## Compliance

- Standards referenced, not reproduced: DO-160 (RTCA, EUROCAE twin
  ED-14) section 21 is referenced by name. The CE102 and RE102 limit
  values in this leaf and its logic module are paraphrased
  reference-only typical values, explicitly NOT the normative RTCA
  table; the normative limits come from the current RTCA/DO-160
  revision and must be verified against it before any qualification
  decision (standards-map.yaml).
- compliance: STANDARDS-REF, gated: false.
