---
name: e2001-multicarrier-analysis-levels
description: "Use when determine which of the two multicarrier multipactor design analysis levels ECSS-E-ST-20-01C clause 4.7.2.1 requires for a radio-frequency chain: build the coherent peak-envelope-power of the carrier plan, compare it against the single-carrier multipactor threshold derated by the applicable margin, close the case at the worst-case first level when it fits, and otherwise run the time-resolved second level -- sample the envelope over its beat period, measure the longest dwell above the margined threshold, and hold it against the gap-crossing-rule window set by the credited crossings and resonance-order. Trigger: ecss, e-st-20-01c, multicarrier-multipactor, multipactor-analysis-level, gap-crossing-rule, peak-envelope-power, envelope-dwell-time, resonance-order."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multicarrier-analysis-levels, multicarrier-multipactor, multipactor-analysis-level, gap-crossing-rule, peak-envelope-power, envelope-dwell-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Multicarrier Analysis Levels (space-systems/ecss/e2001-multicarrier-analysis-levels)

Use when the task is the analysis-level choice of ECSS-E-ST-20-01C clause
4.7.2.1 -- deciding whether a multicarrier multipactor assessment can be closed
by the simple worst-case envelope check, or whether it has to be taken to the
time-resolved check that credits how briefly the envelope sits above the
margined threshold.

## Domain quick reference

- The two levels are not alternatives to pick by taste. The first level is a
  bounding check: every carrier is taken to add in phase, giving the coherent
  peak-envelope-power `(sum of sqrt(P_i))^2`, which is compared against the
  single-carrier multipactor threshold derated by the required margin. Passing
  it closes the case, because nothing the real envelope does can exceed that
  bound.
- The second level is only entered when the bound is exceeded. It credits the
  physics the bound throws away: multipactor needs time to build, so an
  excursion above the margined threshold is tolerated while it lasts less than
  the time an electron needs for the credited number of gap crossings. A gap
  crossing takes half an RF period at first-order resonance, so the window is
  short -- tens of picoseconds at Ku-band for twenty crossings.
- The envelope of a multicarrier plan repeats at the greatest common divisor of
  the carrier offsets, which is the spacing for an evenly spaced plan and a
  coarser beat for an irregular one. The dwell above a level is measured over
  exactly one such period; sampling that is too coarse for the fastest beat in
  the plan is rejected rather than reported.
- The window is taken at the highest carrier in the plan, whose gap crossings
  are the quickest and whose tolerated excursion is therefore the shortest.
- Wide carrier spacing helps and narrow spacing hurts: the same excursion depth
  lasts proportionally longer when the beat is slow, which is why a chain with
  closely spaced carriers usually fails the second level even though a widely
  spaced chain at the same powers passes.

## Workflow

1. Validate the carrier plan -- at least two carriers, finite positive
   frequency and power each, no two carriers at the same frequency.
2. Compute the coherent peak-envelope-power of the plan and derate the
   single-carrier multipactor threshold by the required margin.
3. Run the first level: if the peak envelope sits within the derated
   allowance, record the level-1 verdict and stop -- the second level adds
   nothing to a case the bound already closes.
4. Where the bound is exceeded, record the overshoot and declare the second
   level required, together with the inputs it needs and the first level never
   asked for: carrier frequencies, resonance order, credited gap crossings.
5. Derive the beat period of the envelope from the greatest common divisor of
   the carrier offsets, and sample one full period finely enough to resolve the
   fastest beat in the plan.
6. Measure the longest contiguous dwell above the derated allowance, treating
   the period as circular so an excursion straddling the period boundary is not
   cut in two.
7. Compare the dwell against the gap-crossing window at the highest carrier;
   the chain passes the second level only when the dwell stays inside it, and
   the shortfall is reported in seconds when it does not.

## Pitfalls

- Going straight to the time-resolved level because it is the more detailed
  one; when the worst-case bound already closes, the extra inputs it needs are
  unjustified assumptions carried into the verification file.
- Taking the first level's peak from the summed average power of the carrier
  plan instead of the coherent sum of amplitudes -- the in-phase peak of N
  equal carriers sits N times the average, not at it.
- Applying the gap-crossing window at the lowest carrier, or at the beat
  frequency, instead of the highest carrier; both stretch the tolerated
  excursion and let a chain pass that the conservative choice fails.
- Sampling the envelope over a fixed time span rather than one full beat
  period, or with too few samples for an irregularly spaced plan, so the dwell
  is measured on aliased structure.
- Measuring the dwell without wrapping the period, which cuts the excursion
  around the in-phase peak in half and doubles the apparent compliance.
- Widening the credited number of gap crossings to make a chain pass; the
  crossings are a project-agreed input, and only floating-point representation
  error is absorbed at the comparison, by a named tolerance.

## Behavior contract (gate 3)

The plan validation, envelope arithmetic, beat-period derivation,
level-selection, dwell measurement and gap-crossing comparison logic is
exercised by the gate 3 contract test:
scripts/test_e2001_multicarrier_analysis_levels.py against
scripts/e2001_multicarrier_analysis_levels_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multicarrier_analysis_levels.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
