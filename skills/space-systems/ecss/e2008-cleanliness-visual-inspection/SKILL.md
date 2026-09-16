---
name: e2008-cleanliness-visual-inspection
description: "Use when a coupon has been looked at and the cleanliness result needs a bound the examination can support. Assess whether the surfaces of a photovoltaic coupon appear clean to the unaided eye under ECSS-E-ST-20-08C clause 5.5.3.2.21: derive the detection floor from the working distance and eye acuity, flag a record made through a magnifier as a different and more sensitive instrument, check illuminance and viewing distance, disposition particulate, films, fingerprints, adhesive residue, staining and fibres, add small deposits into a coverage fraction, and report the verdict together with the feature size it is bounded at. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-21, coupon-surface-cleanliness, unaided-visual-detection-floor, particulate-deposit-disposition, cleanliness-inspection-illuminance-floor, magnification-aid-out-of-scope."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-cleanliness-visual-inspection, coupon-surface-cleanliness, unaided-visual-detection-floor, particulate-deposit-disposition, cleanliness-inspection-illuminance-floor, magnification-aid-out-of-scope, solar-coupon-contamination-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Cleanliness Visual Inspection (space-systems/ecss/e2008-cleanliness-visual-inspection)

Use when the task is the cleanliness look of ECSS-E-ST-20-08C clause
5.5.3.2.21 -- deciding whether the surfaces of a coupon appear clean when
they are examined with no magnification aid, and saying how much that
appearance is worth.

## Domain quick reference

- The words that do the work in the clause are "appearing clean" and "without
  magnification aids". Both are bounds, not decoration. The first says the
  output is an appearance under stated conditions, the second fixes the
  instrument that produced it.
- The unaided eye resolves roughly one arc minute, which at a 300 mm working
  distance is about 0.09 mm. That number is a detection floor: below it the
  examination reports nothing, so a surface that looks clean is clean down to
  the floor and silent above it. The floor is reported with the verdict, not
  left implicit.
- The floor scales with the working distance. Standing back doubles it, and a
  surface examined from arm's length carries a weaker statement than the same
  surface examined at 300 mm even though both records say "clean".
- A magnifier is a more sensitive instrument, not a better version of the same
  one. Its record answers a different question: it can find deposits the
  clause never asked about, and it cannot be credited as the unaided look. It
  is flagged rather than silently folded in.
- Illuminance is the other half of the optics. Below roughly a thousand lux a
  surface look stops being a detection activity whatever the eye in front of
  it is capable of, so an under-lit record withholds the clean statement.
- Deposit kinds separate by what has to happen next, not by size. A removable
  film is cleaned and looked at again. A fingerprint is ionic and hygroscopic
  and is never accepted at size. A stain is a change of the surface itself, so
  cleaning does not answer it. A fibre bridges between features, so its length
  matters and its footprint does not.
- A particle recorded below the detection floor did not come from an unaided
  look. The record is more likely to be a transcription from a different
  examination than a very sharp-eyed inspector, so it goes to review.
- Small deposits still accumulate. A coverage fraction over the surface catches
  the face that passed every individual limit and is nevertheless filmed over.

## Workflow

1. Take the declared surface count for the coupon and the records. Reject a
   record set larger than the declared count, and report the shortfall when it
   is smaller; a coupon is only as clean as the face nobody looked at.
2. Per surface, derive the detection floor from the working distance, the
   acuity and any magnification, and keep the unaided floor beside it.
3. Check the examination conditions: magnification at unity, working distance
   inside its limit, illuminance at or above the floor. A condition not met
   withholds the clean statement for that surface rather than failing it
   silently.
4. Disposition every deposit against its own rule, sending anything recorded
   below the detection floor to review.
5. Sum the deposit areas into a coverage fraction and escalate when the
   fraction exceeds the allowance even though no single deposit did.
6. Roll up: the worst surface verdict, the surfaces that are not accepted, the
   completeness flag, and the largest detection floor across the coupon --
   which is the size the whole clean statement is bounded at.

## Pitfalls

- Reporting "clean" with no floor attached. The examination did not look for
  anything smaller than its floor, so the bare word overstates what is in
  hand.
- Treating a magnified record as a better unaided one. It is a different
  instrument with a different threshold, and folding it in changes the
  acceptance criteria without anyone deciding to.
- Ignoring the working distance. The floor scales with it, so two records that
  both say clean can be worth four times as much detection as each other.
- Accepting an under-lit examination because it found nothing. Finding nothing
  is the expected result of looking in the dark.
- Grading a fingerprint on area. Its size is not the problem; the ionic
  residue is, and it draws water for as long as it is left there.
- Cleaning a stain. The surface itself has changed, so a re-inspection after
  cleaning reports the same thing and consumes a handling cycle.
- Using a fibre's length as its footprint. It bridges rather than sits, so the
  length drives the disposition and the area does not.
- Accepting a surface because every deposit passed. The coverage fraction
  exists for exactly that case.
- Comparing a measurement with a derived limit by bare arithmetic. The floor
  comes out of a trigonometric conversion and the deposit limits are products
  of a criteria value and a measured area, so a measurement exactly on a limit
  can evaluate a few units in the last place above it; the comparison absorbs
  that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The detection floor derivation, magnification and illuminance condition
checks, per-kind deposit dispositioning, the below-floor record rule, the
coverage fraction and the coupon completeness rollup are exercised by the
gate 3 contract test:
scripts/test_e2008_cleanliness_visual_inspection.py against
scripts/e2008_cleanliness_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_cleanliness_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
