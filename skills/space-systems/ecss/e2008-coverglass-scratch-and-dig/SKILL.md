---
name: e2008-coverglass-scratch-and-dig
description: "Use when coverglass surfaces have been examined and each needs a disposition. Evaluate the scratches and digs on a solar-cell coverglass against the largest sizes its source control drawing fixes, under ECSS-E-ST-20-08C clause 8.7.1.3.2: read the drawing designation into a scratch grade and a dig grade, refuse to grade a part with no drawing or a superseded revision, convert each measured width and diameter into a grade through the declared units, hold back features in the edge exclusion band, sum the grade-weighted scratch length and the dig concentration, and roll the lot up. Trigger: ecss, e-st-20-08c, clause-8-7-1-3-2, coverglass-scratch-and-dig-limits, source-control-drawing-surface-quality, scratch-grade-conversion, dig-grade-concentration-sum, coverglass-surface-defect-disposition."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-scratch-and-dig, coverglass-scratch-and-dig-limits, source-control-drawing-surface-quality, scratch-grade-conversion, dig-grade-concentration-sum, coverglass-surface-defect-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Scratch and Dig (space-systems/ecss/e2008-coverglass-scratch-and-dig)

Use when the task is the scratch and dig screen of ECSS-E-ST-20-08C
clause 8.7.1.3.2 -- a solar-cell coverglass examined for surface
scratches and digs, with the largest permitted sizes taken from the
coverglass source control drawing rather than from any general figure.

## Domain quick reference

- The limits are an input, not a constant. The drawing for that
  coverglass fixes the largest scratch and the largest dig, so a screen
  run with no drawing in hand has nothing to grade against; substituting
  a house figure grades the part against a requirement nobody imposed
  and produces a disposition that cannot be defended.
- The drawing revision is part of the limit. A part released against an
  earlier revision was accepted to that revision's numbers, and grading
  it against the current sheet either condemns a compliant part or
  passes a non-compliant one.
- A grade is a designation, not a length. The scratch grade becomes a
  width, and the dig grade a diameter, only through the unit the drawing
  declares, so a measured millimetre figure is converted to a grade
  before anything is compared and the two are never compared directly.
- The largest feature is not the whole question. A face with nothing
  oversize on it can still carry too much: the graded scratches are
  summed as length weighted by their grade, and the graded digs are
  summed as grade over the aperture, and either sum can take a part out
  on its own.
- Where a feature sits decides whether it counts. A dig inside the
  declared edge exclusion band is out of the optical path and is
  reported rather than graded, so an oversize feature there does not
  take the part out.
- A scratch cannot be worked out of glass. The disposition between
  accept and reject is referral to the drawing authority, not rework, so
  the middle band is a review band and nothing is sent back to be
  polished.
- An absent record is not a clean part. An empty feature list means
  examined and clean; no feature list at all means not examined, and the
  two must not collapse into each other.

## Workflow

1. Read the drawing designation into a scratch grade and a dig grade and
   refuse a callout that is not two numbers or that carries a zero.
2. Validate the rest of the drawing: identifier, revision, the scratch
   and dig units, the aperture reference dimension, the edge exclusion
   band and the two aggregate allowances.
3. Resolve the grades into the millimetre figures they mean, and scale
   the aggregate allowances to the aperture reference dimension.
4. Check each coverglass names the same drawing and the same revision
   the limits came from; either mismatch is refused rather than graded.
5. Measure every recorded feature: convert a scratch width and a dig
   diameter into a grade, take the distance from the edge, and hold back
   whatever falls inside the exclusion band.
6. Grade each graded feature against its own limit, placing anything
   past it into the review band or past the review band into rejection.
7. Sum the grade-weighted scratch length and the dig grade across the
   aperture and place both against their allowances, so a face of
   individually acceptable features can still fail.
8. Roll the lot up: how many parts carry a finding, how much of the lot
   allowance is left, which parts were never examined and which carry no
   record, then report the worst disposition and the completeness flag.

## Pitfalls

- Running the screen with a default limit because the drawing was not to
  hand. The clause says the drawing fixes the sizes; a default is a
  different requirement wearing the same number.
- Grading a part against the current revision of its drawing when it was
  released against an earlier one.
- Comparing a measured width in millimetres with a scratch grade. They
  are different quantities and the comparison silently passes or fails
  by three orders of magnitude.
- Assuming the dig unit. It is declared on the drawing, and a drawing
  that declares a different one moves every millimetre limit while
  leaving the grades alone.
- Grading only the largest feature. The aggregate scratch length and the
  dig concentration each fail independently of it.
- Counting features that sit in the edge exclusion band. They are out of
  the optical path, and folding them in condemns parts that are fit.
- Offering rework on a scratched coverglass. Glass does not give the
  surface back; the middle disposition is referral to the drawing
  authority.
- Reading a missing feature list as an unmarked part. Absence is not
  zero, and a part nobody looked at leaves the lot open.
- Comparing a grade or an aggregate sum with its limit by bare
  arithmetic. A grade is a measured millimetre figure divided by a
  declared unit of a thousandth or a hundredth of a millimetre and
  neither the unit nor the quotient is exactly representable, so a
  feature measured exactly at the drawing limit lands a few units in the
  last place either side of it and differently on different machines;
  the comparison absorbs that representation error while the drawing
  limit stays untouched.

## Behavior contract (gate 3)

The designation parse, the drawing validation and its refusal of a
missing drawing, the resolution of grades into millimetres through the
declared units, the drawing and revision match on each part, the
per-feature grade conversion and edge-band hold-back, the grade limit
with its review band, the grade-weighted scratch length and dig
concentration sums, and the lot allowance with its remaining budget and
completeness rollup are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_scratch_and_dig.py against
scripts/e2008_coverglass_scratch_and_dig_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_scratch_and_dig.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
