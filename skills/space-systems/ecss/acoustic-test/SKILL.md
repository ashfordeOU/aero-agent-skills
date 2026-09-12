---
name: acoustic-test
description: "Use when perform acoustic test verification of a spacecraft structure per ECSS-E-ST-32C clause 4.6.3.10: derive the 1/3-octave band test spectrum from the launch acoustic environment, apply the qualification margin to acceptance levels, compute the Overall Sound Pressure Level (OASPL), verify frequency range covers 31.5 Hz to 10 kHz, check test duration against the category minimum, and assess band-by-band spectrum compliance within tolerance. Categorize the test as qualification, acceptance, or protoflight; flag duration shortfalls, frequency coverage gaps, and spectrum underdrive or overdrive. Trigger: ecss, e-st-32-structures-scope, acoustic-test, acoustic-noise, oaspl, sound-pressure-level, vibro-acoustic, structural-test."
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
  tags: [ecss, e-st-32-structures-scope, acoustic-test, acoustic-noise, oaspl, sound-pressure-level, vibro-acoustic, structural-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Acoustic Test (space-systems/ecss/acoustic-test)

Use when the task is acoustic test verification of a spacecraft structure
per ECSS-E-ST-32C clause 4.6.3.10 — deriving the 1/3-octave test spectrum,
applying qualification margins, computing OASPL, and checking measured
spectrum compliance against required levels for a given test category.

## Domain quick reference

- Acoustic tests expose spacecraft structures to high-intensity broadband
  acoustic noise representing the launch environment. The test spectrum is
  defined in 1/3-octave bands spanning at least 31.5 Hz to 10 000 Hz.
- Three test categories apply: qualification (demonstrates margin over the
  maximum expected environment), acceptance (screens workmanship at the
  expected level), and protoflight (qualification duration and margin applied
  to a flight unit). Each category carries a minimum test duration in seconds.
- The qualification spectrum is derived from the acceptance spectrum by adding
  a positive margin (typically +3 dB per band). The qualification margin is
  applied uniformly across all bands before the test is set up.
- The Overall Sound Pressure Level (OASPL) is the power sum of all 1/3-octave
  band contributions. Two bands at the same level produce an OASPL 3 dB higher
  than either band alone.
- During a test run the facility controller maintains the measured spectrum
  within a tolerance band (typically ±1 dB per band) around the required
  levels. Bands persistently outside that window constitute either underdrive
  (insufficient excitation) or overdrive (over-test risk).

## Workflow

1. Confirm the test category (qualification, acceptance, or protoflight) and
   retrieve the acceptance-level 1/3-octave spectrum from the acoustic
   environment specification. Reject an unrecognized category before
   proceeding.
2. If the category requires a qualification margin, apply the margin (in dB)
   to each acceptance-level band value to obtain the required test spectrum.
   Protoflight uses the same margin as qualification.
3. Verify that the spectrum's frequency axis covers the required range from
   31.5 Hz to 10 000 Hz. Flag any gap at the low end or the high end as a
   frequency coverage finding before the test run is approved.
4. Check that the planned test duration equals or exceeds the category minimum
   (120 s for qualification and protoflight; 60 s for acceptance). Flag a
   shortfall as a duration finding.
5. Compute the OASPL for the required spectrum by power-summing all band levels.
   Record this value as the expected OASPL for comparison with the measured
   result.
6. After the test run, compare each measured band level against the required
   level within the tolerance window. Collect underdrive findings (measured
   below required minus tolerance) and overdrive findings (measured above
   required plus tolerance).
7. Compute the measured OASPL and compare it against the required OASPL.
   Aggregate all findings (duration, frequency coverage, spectrum compliance);
   the test is compliant only when every finding list is empty.

## Pitfalls

- Applying the qualification margin to measured levels instead of required
  levels — the margin is set on the control spectrum before the test begins,
  not derived after the fact from measured data.
- Omitting frequency coverage verification and accepting a spectrum that stops
  at 8 000 Hz — a gap in the highest decade of the acoustic range leaves
  high-frequency structural modes unexcited.
- Treating OASPL as a per-band compliance metric — OASPL is a summary
  indicator computed by power summation; a compliant OASPL does not guarantee
  every individual band is within tolerance.
- Confusing acceptance and protoflight categories: protoflight applies a
  qualification-level margin and qualification duration to a flight unit, so
  its minimum duration and level requirements are the same as qualification,
  not acceptance.
- Using arithmetic (linear) summation of band levels instead of power summation
  when computing OASPL — linear addition overestimates OASPL and defeats the
  3 dB coherence rule for equal-level bands.

## Behavior contract (gate 3)

The SPL arithmetic, OASPL computation, margin application, frequency coverage
check, duration check, spectrum compliance check, and full-review logic are
exercised by the gate 3 contract test: scripts/test_acoustic_test.py against
scripts/acoustic_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_acoustic_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
