---
name: e2008-full-visual-inspection-process
description: "Use when an inspection record has to be graded for examination adequacy rather than for the defects it happened to find. Verify that the visual examination of a photovoltaic assembly coupon was carried out against each detailed inspection requirement of ECSS-E-ST-20-08C clause 5.5.3.2.2: derive the magnification a requirement demands from its smallest detectable feature and a declared resolution-element count, compare that with the magnification applied, place the working illuminance inside or outside the band the requirement sets, list the viewing aspects the examination never took, and confirm the build stage the requirement is written against was actually performed. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-visual-inspection, inspection-magnification-adequacy, coupon-viewing-aspect-coverage, inspection-illumination-band, inspection-stage-coverage, resolvable-feature-size."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-full-visual-inspection-process, photovoltaic-assembly-visual-inspection, inspection-magnification-adequacy, coupon-viewing-aspect-coverage, inspection-illumination-band, inspection-stage-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Full Visual Inspection Process (space-systems/ecss/e2008-full-visual-inspection-process)

Use when the task is the examination procedure of ECSS-E-ST-20-08C
clause 5.5.3.2.2 -- how the visual inspection of a photovoltaic assembly
coupon is actually performed against every detailed inspection
requirement, and whether the way it was performed could have found what
each requirement asks for.

## Domain quick reference

- A detailed inspection requirement names a feature the examination has
  to be capable of finding: an edge chip on a coverglass, a lifted
  interconnect foot, a void in an adhesive fillet. Grading the
  examination means grading that capability, not counting the defects
  that happened to be written down.
- Four recorded conditions decide the capability. Magnification sets the
  smallest detail resolvable at all; illumination sets whether the
  contrast to see it exists; the viewing aspects taken set whether the
  feature was ever in the field of view; and the build stage at which
  the examination happened sets whether the feature was still visible.
- The resolution model is arithmetic, not judgement. A trained unaided
  eye resolves about a tenth of a millimetre at the reference viewing
  distance, so under magnification M the resolvable detail is that
  reference divided by M. A feature is only reliably found when several
  resolution elements fall across it, which fixes the demanded
  magnification as reference times element-count divided by the smallest
  feature. The element count is a declared inspection policy.
- Illumination is a band, not a floor. Too little light hides a low
  contrast chip; too much specular light off a coverglass washes one out
  just as effectively, so an over-lit examination is a finding in the
  same way an under-lit one is.
- Stage coverage is the trap that survives a good inspection sheet. A
  rear-face interconnect visible only before the coupon is bonded down
  cannot be examined afterwards, so a requirement written against a
  stage the process never performed is unsatisfied no matter how good
  the optics were.
- The requirement with the least magnification head-room governs the
  examination: it is the one that decides the optics the whole process
  has to be set up with.

## Workflow

1. Validate the process record: magnification at unity or above,
   a positive working illuminance, at least one viewing aspect, at least
   one build stage performed, and a declared resolution-element count.
   Reject an unknown aspect or stage rather than dropping it silently.
2. Validate each detailed requirement: an identifier, a positive
   smallest detectable feature, the stage it is written against, the
   aspects it needs, and its illuminance band.
3. For each requirement, compute the demanded magnification from the
   smallest feature and the element count, and the detail the applied
   magnification actually resolves. Compare the two through their ratio,
   absorbing representation error at an exact match with a named
   tolerance rather than by relaxing the demand.
4. Place the working illuminance against that requirement's band and
   record below-band or above-band as distinct outcomes.
5. Subtract the aspects viewed from the aspects the requirement needs,
   and check the requirement's stage against the stages performed.
6. Return a per-requirement verdict with its findings, then the run
   verdict: the coverage fraction, the governing requirement, and any
   aspect the examination took that no requirement asked for.

## Pitfalls

- Grading the inspection by its defect list. An examination that found
  nothing because it was run at four magnifications too low reads as a
  clean coupon; the capability check is what separates the two.
- Clamping a demanded magnification below unity up to unity. A large
  feature genuinely needs no aid, and clamping throws away the head-room
  that tells you which requirement is really governing.
- Treating illumination as a minimum. A specular coverglass over-lit
  past the band loses the very chip the requirement targets, so the
  upper bound is a real limit and not a formality.
- Accepting an examination performed at the wrong point in the build.
  Access, not optics, is what a post-bond inspection loses, and no
  amount of magnification recovers a surface that is now face-down.
- Asserting a strict inequality on the magnification ratio when the
  applied magnification is meant to sit exactly on the demand. The ratio
  is a quotient of computed quantities and can land a few units in the
  last place either side of one; compare it to the bound with a
  tolerance and keep the assertion about what the code then decides.

## Behavior contract (gate 3)

The resolution model, illuminance banding, aspect-gap subtraction, stage
coverage, per-requirement verdict and run roll-up are exercised by the
gate 3 contract test:
scripts/test_e2008_full_visual_inspection_process.py against
scripts/e2008_full_visual_inspection_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_full_visual_inspection_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
