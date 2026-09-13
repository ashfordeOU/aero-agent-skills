---
name: e2008-bleed-resistor-test
description: "Verify the bleed resistor fitted to a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.5.3.3.5: resolve the acceptance band from the drawing nominal and its tolerance, refer the reading back to the reference temperature through the element coefficient, de-embed an in-circuit reading against the declared parallel path and refuse to sentence one without it, grade both band edges separately, then work out whether the measured part drains the assembly capacitance to a safe voltage in the time the safety case assumes. Use when a bleed resistor measurement has to be accepted, sentenced or repeated. Trigger: ecss, e-st-20-electrical-scope, bleed-resistor-resistance-measurement, photovoltaic-assembly-bleed-path, in-circuit-parallel-deembedding, bleed-resistor-tolerance-band, assembly-discharge-time-constant, safe-voltage-bleed-time."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-bleed-resistor-test, bleed-resistor-resistance-measurement, photovoltaic-assembly-bleed-path, in-circuit-parallel-deembedding, bleed-resistor-tolerance-band, assembly-discharge-time-constant, safe-voltage-bleed-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bleed Resistor Test (space-systems/ecss/e2008-bleed-resistor-test)

Use when the task is the bleed resistor test of ECSS-E-ST-20-08C clause
5.5.3.3.5 -- measuring the resistance of the bleed resistor fitted to a
photovoltaic assembly and deciding whether the part that is actually on the
assembly is the part the drawing specifies and does the job it was fitted for.

## Domain quick reference

- The reading is evidence twice over. It grades the part against the drawing
  band, and it grades the drain the assembly will actually get, which is what
  the resistor was fitted to provide in the first place.
- An in-circuit reading is never the resistor. It is the parallel combination
  of the resistor and everything else across it, so it always reads low; a
  part sentenced on an undeembedded in-circuit reading is scrapped for a fault
  that lives in the harness around it.
- De-embedding needs a declared parallel path. Without one the in-circuit
  reading is carried as not evaluated rather than compensated by a guess, and
  a parallel value that does not exceed the reading is refused outright
  because a parallel combination always sits below either arm.
- The element has a temperature coefficient, so the reading is referred back
  to the reference temperature before the band comparison. On a part with a
  tight tolerance a twenty-kelvin offset is a visible fraction of the band.
- The two band edges mean different things. Above the band the assembly drains
  too slowly and stays live longer than the safety case assumes; below it the
  resistor bleeds current the array was not sized to give away and dissipates
  more than it was rated for.
- The drain itself is a single exponential, so the time to fall from the
  initial voltage to the safe voltage is the time constant scaled by the
  natural logarithm of the voltage ratio. An in-band part on an assembly with
  more capacitance than assumed can still miss that time.
- Band edges are inclusive. A part landing exactly on an edge is a pass, so
  the comparison absorbs representation error instead of the band being
  widened to make the arithmetic tidy.

## Workflow

1. Validate the drawing values: a positive nominal, a symmetric tolerance
   fraction or an asymmetric pair, a coefficient, a reference temperature, and
   an open threshold that sits above the band ceiling.
2. Resolve the acceptance band from the nominal and the tolerance, honouring
   an asymmetric tolerance on both sides.
3. Read the measurement configuration first. An out-of-circuit reading is the
   part; an in-circuit reading is de-embedded against the declared parallel
   path, or carried as not evaluated when none was declared.
4. Refer the resulting resistance back to the reference temperature with the
   element coefficient, refusing a combination that inverts the linear model.
5. Grade the referred value: open, below the band floor, above the band
   ceiling, or inside it, and say which edge was crossed.
6. Work out the drain the measured part delivers -- the time constant against
   the assembly capacitance, and the time to fall from the initial voltage to
   the safe voltage -- and compare it with the time the safety case allows.
7. Roll the value verdict and the drain verdict into one result, verified only
   when the part is in band and the assembly reaches safe in time, and report
   every finding from both halves.

## Pitfalls

- Measuring the resistor in circuit and sentencing the low reading. The
  parallel paths are inside the number, and the part being pulled off the
  assembly is usually good.
- De-embedding with an assumed parallel value. A guessed path moves the
  recovered value by as much as the tolerance band is wide, so an undeclared
  parallel path leaves the reading inconclusive.
- Comparing a warm reading with a band written at the reference temperature. A
  tight-tolerance part flips verdicts on a temperature offset alone.
- Reading the band as a one-sided limit. A resistor below the floor is a
  dissipation and load problem, not a conservative pass.
- Stopping at the value. A part inside its band still leaves the assembly live
  too long when the capacitance is larger than the one the band was chosen
  against, which is the whole reason the resistor is there.
- Widening the band so a part exactly on an edge counts. Edges are already
  inclusive; the tolerance belongs inside the comparison.

## Behavior contract (gate 3)

The drawing validation and band resolution, the temperature referral, the
in-circuit de-embedding and its refusal, the four value verdicts, the
discharge time constant and bleed time, and the roll-up into one verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_bleed_resistor_test.py against
scripts/e2008_bleed_resistor_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_bleed_resistor_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
