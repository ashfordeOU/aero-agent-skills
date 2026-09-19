---
name: q7001-particulate-verification-methods
description: "Convert a particulate cleanliness measurement into a number the requirement can be graded against. Use when a tape lift, a vacuum sample, an exposed fallout plate or an optical count has come back under ECSS-Q-ST-70-01C and the raw bins still have to become an obscuration: subtract the sampling-medium blank bin by bin and refuse a blank larger than the sample, scale the counts up for the fraction a lifting method leaves behind, normalise to the sampled area, sum the projected circle areas into a percentage, divide a plate reading by its exposure to get a deposition rate, and grade the result at the allowed value. Trigger: ecss, q-st-70-01c, particulate-obscuration-percent, particle-fallout-plate-rate, tape-lift-recovery-fraction, vacuum-sampling-minimum-area, particle-count-blank-subtraction, particulate-size-distribution-bins."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-particulate-verification-methods, particulate-obscuration-percent, particle-fallout-plate-rate, tape-lift-recovery-fraction, vacuum-sampling-minimum-area, particle-count-blank-subtraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Particulate Measurement Methods (space-systems/ecss/q7001-particulate-verification-methods)

Use when the task is the particulate measurement step of cleanliness
verification under ECSS-Q-ST-70-01C: a size distribution has come off a
tape lift, a vacuum sample, an exposed fallout plate or an optical
counter, and it has to be reduced to a per-area figure that the
cleanliness requirement can be graded against.

## Domain quick reference

- Obscuration is the quantity the methods agree on. Counts alone do not
  compare across methods or across surfaces; the projected area the
  particles cover, expressed as a percentage of the area sampled, does.
- A lifting method reports what it removed, not what was there. Tape
  lift and vacuum sampling both leave a fraction behind, so the reading
  is scaled up by a recovery efficiency declared for that surface and
  that run, and a reading without one is not yet a result.
- The sampling medium carries its own particles. A blank of the same
  tape lot or filter, counted in the same bins, is subtracted before
  anything else; a blank exceeding the sample in a bin is a failed
  control, not a negative count to be clamped at zero.
- A fallout plate measures a rate, not a state. Its obscuration divided
  by the hours it was exposed gives a deposition rate, and a projection
  onto a longer exposure assumes that rate holds -- an assumption the
  environment has to justify.
- Bin edges have to line up. A blank counted on different edges cannot
  be subtracted bin by bin, and silently matching the nearest edge moves
  counts between size bands.
- Method applicability is decided before sensitivity. An adhesive lift
  on a coated optic, or a vacuum head on a few square centimetres, is
  ruled out by the surface regardless of the detection floor it offers.

## Workflow

1. Validate the distribution: strictly increasing diameters in
   micrometres, non-negative integer counts, and a positive sampled area.
2. Subtract the sampling-medium blank bin by bin, refusing an unmatched
   bin edge or a blank count above the sample count.
3. Apply the recovery efficiency when the method removed the particles;
   refuse a lifting method that arrives without one, and flag a recovery
   declared for a method that samples without removal rather than
   applying it.
4. Normalise the corrected counts to one square metre and sum the
   projected circle areas into an obscuration percentage.
5. For a fallout plate, divide the obscuration by the exposure hours to
   get the deposition rate and project it over the exposure of interest.
6. Compare the obscuration with the allowed value, absorbing
   representation error at the boundary with a named relative tolerance
   instead of relaxing the limit.
7. Report the obscuration, the per-square-metre distribution, the total
   count, any rate and projection, and the findings raised.

## Pitfalls

- Reporting a raw count as a cleanliness result. The same count over a
  different sampled area is a different surface condition, and two
  methods counting differently sized particles are not comparable at all.
- Skipping the recovery correction because the efficiency is unknown.
  An undeclared efficiency does not default to unity; it makes the
  reading a lower bound that cannot substantiate a limit.
- Clamping a negative blank-corrected count to zero. That hides a
  sampling-medium control failure whose other bins are equally suspect.
- Projecting a fallout rate across a phase with a different environment.
  The rate belongs to the exposure it was measured over, so a projection
  into a cleaner or dirtier phase needs its own plate.
- Grading a largest-particle observation against an area-coverage limit.
  One large particle and many small ones can share an obscuration while
  failing entirely different requirements.
- Choosing a method on detection floor alone. Adhesive tolerance and
  minimum sampled area rule methods out before sensitivity is reached.

## Behavior contract (gate 3)

The distribution validation, blank subtraction, recovery correction,
per-area normalisation, obscuration summation, fallout rate and
projection, method applicability and the boundary-tolerant grading are
exercised by the gate 3 contract test:
scripts/test_q7001_particulate_verification_methods.py against
scripts/q7001_particulate_verification_methods_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_particulate_verification_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
