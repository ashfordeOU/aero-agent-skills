---
name: q6005-physical-dimension-verification
description: "Verify a finished hybrid package against its drawing tolerances and the host site it has to enter, under ECSS-Q-ST-60-05C clause 10.3.8. Use when the task is holding asymmetric plus and minus limits apart instead of folding them, grading a reading against those limits with its own measurement uncertainty in hand, judging whether the gauge can resolve the tolerance band at all, fitting the largest package the drawing permits into the site with its keep-out intact, and accumulating terminal position along a long row. Trigger: ecss, q-st-60-05c, hybrid-package-dimension-verification, asymmetric-drawing-tolerance-limits, dimensional-measurement-uncertainty-guard-band, gauge-capability-tolerance-ratio, worst-case-package-envelope-fit, terminal-pitch-position-accumulation."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-physical-dimension-verification, hybrid-package-dimension-verification, asymmetric-drawing-tolerance-limits, dimensional-measurement-uncertainty-guard-band, worst-case-package-envelope-fit, terminal-pitch-position-accumulation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Physical Dimension Verification (space-systems/ecss/q6005-physical-dimension-verification)

Use when the task is the dimensional check of ECSS-Q-ST-60-05C clause
10.3.8 — measuring the finished package against its drawing and
deciding whether what was measured will actually go into the host
assembly it was built for.

## Domain quick reference

- A tolerance is two numbers. A dimension permitted to grow a little
  and shrink a lot has an asymmetric band, and folding it into one
  plus-or-minus figure moves whichever limit was the tighter of the
  two. The utilization of the band is read against the side the
  reading went, not against half the total width.
- A reading arrives with an uncertainty and the decision has to carry
  it. A value inside a limit by less than the expanded uncertainty has
  not been shown to conform; the honest status is that conformity is
  not shown, and recording it as a pass hands the decision to the noise
  in the gauge.
- The gauge is checked before the part. When the uncertainty interval
  is a large fraction of the tolerance band the instrument cannot
  resolve the requirement at all, and every reading it produced is a
  statement about the instrument rather than about the hardware.
- The fit is judged at worst case. The site has to accept the largest
  package the drawing permits, with the keep-out clearance still
  intact. A nominal package that fits and a maximum-material package
  that does not is a drawing that passes incoming inspection and fails
  at assembly.
- A per-pitch tolerance does not stay per-pitch. Over a row of
  terminals it accumulates - linearly in the worst case, as the square
  root of the span statistically - and the terminal at the far end of
  the row is the one that misses its pad. Which accumulation applies is
  a stated choice, not a default.

## Workflow

1. Validate each dimension: name, nominal, both tolerances, the
   reading and its expanded uncertainty. A zero-width band, a negative
   tolerance, a non-positive nominal or reading and a repeated
   dimension name are input errors.
2. Derive the two limits from the nominal and the two tolerances
   separately, and compute the signed deviation and the utilization of
   the side the reading used.
3. Compute the gauge capability ratio from the band and the
   uncertainty interval, and raise it as its own finding when the
   instrument cannot resolve the requirement.
4. Grade each reading as within limits, outside them, or not shown
   either way once the uncertainty guard band is applied at both ends.
5. Take the package to its maximum material condition, subtract it and
   the keep-out from the host site, and report the clearance that is
   left rather than a bare pass.
6. Accumulate terminal position along the row by the stated method and
   compare the result with what the host footprint allows.
7. Aggregate the measured sample: accepted and rejected units, the
   worst utilization anywhere in it, and the tightest clearance any
   unit carries.

## Pitfalls

- Folding an asymmetric tolerance into a symmetric one. One of the two
  limits moves, and the parts that fail are the ones the tighter side
  was protecting.
- Passing a reading that sits a micron inside the limit with a gauge
  whose uncertainty is larger than that. Nothing was demonstrated, and
  the same part measured again can be outside.
- Accepting the instrument because it is calibrated. Calibration says
  the reading is traceable, not that its uncertainty is small relative
  to this particular tolerance band.
- Checking the fit at nominal. The drawing permits a larger package
  than the one on the bench, and the site has to take that one too,
  with the keep-out unbroken.
- Treating the pitch tolerance as the position tolerance. Twenty-four
  terminals give twenty-three spans, and the accumulated departure at
  the end of the row is far larger than the tolerance on any one pitch.
- Choosing the statistical accumulation because it is the smaller
  number. It is a statement about a population, and a single part at
  the end of a worst-case run is not covered by it.

## Behavior contract (gate 3)

The two-sided limit derivation, utilization, gauge capability ratio,
uncertainty guard band and three-state status, worst-case envelope fit,
terminal position accumulation and sample aggregation are exercised by
the gate 3 contract test:
scripts/test_q6005_physical_dimension_verification.py against
scripts/q6005_physical_dimension_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_physical_dimension_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
