---
name: e2008-coverglass-boiling-water-test
description: "Use when an immersion run on coated coverglasses must be dispositioned. Evaluate a boiling deionised water immersion of single-coated coverglasses against ECSS-E-ST-20-08C clause 8.7.10: confirm every sample carries a coating on exactly one face, gate the bath on its conductivity, derive the boiling point at the declared ambient pressure rather than assuming a hundred degrees, integrate the bath log to find how long the samples were truly held at or above it instead of ramping towards it, and judge the post-immersion coating loss area against the acceptance fraction. Trigger: ecss, e-st-20-08c-clause-8-7-10, coverglass-boiling-water-immersion, single-coated-coverglass-sample, deionised-bath-water-conductivity, water-boiling-point-at-ambient-pressure, coverglass-coating-loss-area-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-boiling-water-test, coverglass-boiling-water-immersion, single-coated-coverglass-sample, deionised-bath-water-conductivity, water-boiling-point-at-ambient-pressure, coverglass-coating-loss-area-fraction, coverglass-coating-adhesion-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Boiling Water Test (space-systems/ecss/e2008-coverglass-boiling-water-test)

Use when the task is the immersion test of ECSS-E-ST-20-08C clause
8.7.10 -- single-coated coverglasses held in boiling deionised water for
at least a stated time, then inspected -- and the run has to be judged
as evidence before its result is read.

## Domain quick reference

- The test is deliberately blunt. A coating bonded through a
  contaminated interface, an incomplete cure or a porous layer does not
  survive a rolling boil; a properly bonded one comes out unchanged.
  There is no partial credit in the mechanism, which is why the
  conditions of the run matter more than the inspection that follows.
- The sample is single-coated for a reason. A coverglass coated on both
  faces produces a loss nobody can attribute to a face, and the bare
  face on a single-coated sample is the comparison the inspector needs.
  A sample with no coating at all is not a sample either.
- Deionised is a gate, not a label. Water carrying dissolved salts
  leaves them behind as it boils off, and the film they deposit reads as
  coating damage. The bath conductivity is checked before the immersion
  is believed.
- Boiling is not a temperature. Water boils at a hundred degrees only at
  sea-level pressure; a plateau laboratory or a low-pressure day boils
  it several degrees below that, and a bath judged against a hard
  hundred is recorded as never boiling when it was. The threshold comes
  from the declared ambient pressure by Clausius-Clapeyron.
- The duration is hold time, not elapsed time. A log that runs an hour
  but spends twenty minutes climbing to the boil delivered forty minutes
  of immersion. The hold is integrated across the threshold with both
  crossings interpolated.
- A hold far longer than the minimum is a different exposure from the
  one the acceptance was written against, so the actual duration is
  recorded rather than rounded to the requirement.

## Workflow

1. Validate the immersion policy: minimum duration, boil margin,
   conductivity limit, sample count and loss acceptance. A margin wide
   enough to call a warm bath boiling is refused rather than used.
2. Validate each sample and count the ones coated on exactly one face.
   Any sample that is not single-coated closes the run.
3. Check the batch size against the policy minimum; one survivor is not
   a population.
4. Gate the bath on its measured conductivity before any temperature is
   read.
5. Derive the boiling point at the declared ambient pressure and drop
   the policy margin to get the threshold the bath must clear.
6. Validate the bath log, take its peak, and stop when the peak never
   reached the threshold -- the samples were soaked, not boiled.
7. Integrate the hold at or above the threshold, interpolating the
   crossings, and compare it against the minimum duration.
8. Take the worst coating loss fraction across the batch and judge it
   against the acceptance, then close on one verdict and report the
   numbers the verdict rests on.

## Pitfalls

- Judging the bath against a hard hundred degrees. At altitude that
  records a genuinely boiling bath as a failed one, and the clause's
  condition is a boil, not a number.
- Reading the duration off the first and last timestamps. The ramp to
  the boil is not immersion and a log that shows it should not be paid
  for it.
- Running the test in process or tap water because the samples only need
  to get wet. The residue film that leaves is indistinguishable from
  coating loss on inspection.
- Immersing a double-coated coverglass. Whatever comes off cannot be
  attributed to a face, and the run is unusable however clean it was.
- Comparing a hold, a loss fraction or a conductivity with its limit by
  bare arithmetic. Each is a computed quantity, so a run sitting exactly
  on a bound can evaluate a few units in the last place on the wrong
  side of it; the comparisons absorb that representation error while the
  bounds stay untouched.
- Treating an unstated coated-face count or an unstated damaged area as
  zero. Both are refused, because an absent record is not a clean one.

## Behavior contract (gate 3)

The immersion policy validation, the pressure-corrected boiling point
and threshold, the bath log validation and peak, the interpolated hold
time, the water conductivity gate, the single-coated sample check, the
per-sample and worst-case coating loss fractions and the run verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_boiling_water_test.py against
scripts/e2008_coverglass_boiling_water_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_boiling_water_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
