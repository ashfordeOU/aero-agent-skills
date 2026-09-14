---
name: e2008-coverglass-bubbles-and-inclusions
description: "Use when coverglasses have been examined and each needs a disposition. Verify that no bubble or inclusion in a solar-cell coverglass projects more than two hundredths of a square millimetre, under ECSS-E-ST-20-08C clause 8.7.1.3.3: reduce a feature measured as an area, a diameter or two axes to one projected area, refuse a figure finer than the method resolves, group features close enough to cast one shadow and cap the group rather than its members, hold back what sits in the edge exclusion band, sum the area over the aperture, and roll the lot up. Trigger: ecss, e-st-20-08c, clause-8-7-1-3-3, coverglass-bubble-and-inclusion-cap, projected-area-per-inclusion, adjacent-inclusion-grouping, coverglass-aperture-area-budget."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-bubbles-and-inclusions, coverglass-bubble-and-inclusion-cap, projected-area-per-inclusion, adjacent-inclusion-grouping, coverglass-aperture-area-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Bubbles and Inclusions (space-systems/ecss/e2008-coverglass-bubbles-and-inclusions)

Use when the task is the bubble and inclusion screen of ECSS-E-ST-20-08C
clause 8.7.1.3.3 -- a solar-cell coverglass examined for gas bubbles left
in the melt and for solid inclusions carried into it, with the size of
any one of them capped at two hundredths of a square millimetre of
projected area.

## Domain quick reference

- The cap is an area, not a length. What the cell loses is the shadow
  the feature casts on it, so the limit is stated in square millimetres
  and a measured diameter is converted before it is compared. Comparing
  a diameter with an area limit is off by the whole of pi over four and
  in the permissive direction.
- A feature arrives measured in whichever way the method allowed: a
  planimetered area, a diameter, or a major and a minor axis. All three
  reduce to one projected area, and a record carrying two of them is a
  contradiction rather than a cross-check, because nothing says which to
  believe.
- Two features close enough to sit under one shadow are one feature.
  Grading a tight cluster member by member is the usual way a coverglass
  well over the cap passes, so features are grouped by rim-to-rim
  separation first and the group carries the summed area.
- Grouping is single-link along a chain. Three features in a row, each
  close to the next, obscure a continuous strip even where the two ends
  are far apart.
- A figure finer than the method resolves is not a measurement. An
  inclusion recorded at a millionth of a square millimetre by an
  instrument that cannot see it is a transcription, and it is refused
  rather than believed.
- Where the feature sits decides whether it counts. One inside the
  declared edge exclusion band is out of the optical path and is
  reported rather than graded, so an oversize feature there does not
  take the part out.
- The cap is not the only budget. A face whose every feature is under
  the cap can still lose too much of the cell between them, so the
  summed projected area over the active aperture goes against its own
  allowance.
- Glass does not give the inclusion back. The disposition between accept
  and reject is referral to the drawing authority, not rework.
- An absent feature record is not a clear coverglass. An empty list
  means examined and clear; no list at all means not examined, and the
  lot stays open until it is.

## Workflow

1. Validate the allowance set -- the per-feature projected area cap, the
   merge separation, the aperture area allowance, the resolution of the
   method and the review margin -- and refuse a method that cannot
   resolve below the cap.
2. Validate the coverglass geometry and reduce it to the active aperture
   the summed area is taken over.
3. Check each coverglass is the type the aperture was written for.
4. Reduce every recorded feature to one projected area, accepting an
   area, a diameter or a pair of axes but only one of them, and refuse
   anything below the resolution of the method.
5. Take each feature's distance from the edge and hold back whatever
   falls inside the exclusion band as reported rather than graded.
6. Group the graded features by rim-to-rim separation, single-link, and
   give each group the summed area of its members.
7. Place each group against the cap, into the review band or past it,
   and name whether the group was one feature or a cluster of smaller
   ones.
8. Sum the projected area over the active aperture and place it against
   the aperture allowance, then roll the lot up and report the worst
   disposition, the parts not accepted, the remaining allowance and the
   completeness flag.

## Pitfalls

- Comparing a measured diameter with the area cap. The two are different
  quantities and the mistake reads as a pass.
- Taking a feature's bounding box as its projection. An ellipse fills
  pi over four of the box it sits in, so the box over-reports by a
  quarter and condemns parts that are fit.
- Grading a tight cluster member by member. Each is under the cap and
  the shadow they cast together is not.
- Grouping only touching features. The shadow is continuous across a gap
  smaller than the declared merge separation, which is why the grouping
  runs on rim-to-rim distance rather than on overlap.
- Believing a figure below the resolution of the method. It is a
  transcription, not a measurement, and it silently lowers every summed
  area it enters.
- Counting features inside the edge exclusion band. They are outside the
  optical path.
- Passing a face because no single feature is over the cap. Enough
  compliant features still take more of the aperture than the allowance
  permits.
- Reading a missing feature list as a clear coverglass. Absence is not
  zero.
- Comparing a projected area or a summed fraction with its limit by bare
  arithmetic. A projected area is a product of pi with two measured axes
  over four, a fraction divides that by an aperture, and an equivalent
  radius comes back through a square root, so a feature measured exactly
  at the cap lands a few units in the last place either side of it and
  differently on different machines; the comparison absorbs that
  representation error while the cap stays untouched.

## Behavior contract (gate 3)

The allowance validation and its resolution-against-cap check, the
aperture derivation, the three measurement forms reduced to one
projected area with the both-given and swapped-axes refusals, the
resolution floor, the edge-band hold-back, the single-link grouping on
rim-to-rim separation with the group carrying the summed area, the cap
with its review band, the aperture area budget, and the lot allowance
with its remaining budget and completeness rollup are exercised by the
gate 3 contract test:
scripts/test_e2008_coverglass_bubbles_and_inclusions.py against
scripts/e2008_coverglass_bubbles_and_inclusions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_bubbles_and_inclusions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
