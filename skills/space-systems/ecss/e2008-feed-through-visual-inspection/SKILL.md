---
name: e2008-feed-through-visual-inspection
description: "Verify the panel feed-throughs of ECSS-E-ST-20-08C clause 5.5.3.2.17: take each measured centre against its drawing centre as a radial offset, turn the bonded footprint into a coverage fraction and the released run into a share of the bond perimeter, scale the offset and area allowances by the zone the feed-through sits in while leaving the coverage minimum unscaled, and return accept, rework or reject per feed-through with a panel verdict, the loose ones named apart and any drawing feed-through that carries no record held open. Use when panel feed-throughs have been examined and bond and position have to be dispositioned together. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-17, panel-feed-through-bond-verification, feed-through-position-tolerance-check, feed-through-debond-perimeter-fraction, unbonded-feed-through-screen."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-feed-through-visual-inspection, panel-feed-through-bond-verification, feed-through-position-tolerance-check, feed-through-debond-perimeter-fraction, unbonded-feed-through-screen, feed-through-bond-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Feed-Through Visual Inspection (space-systems/ecss/e2008-feed-through-visual-inspection)

Use when the task is the feed-through examination of ECSS-E-ST-20-08C
clause 5.5.3.2.17 -- confirming that every feed-through passing through
the panel substrate is firmly bonded and sitting where the assembly
drawing put it, and turning that into a disposition a rework or a scrap
decision can rest on.

## Domain quick reference

- The clause asks two questions of the same part, and a feed-through
  has to answer both. Bonded but displaced drags the harness off its
  designed run; in position but loose puts the harness load into
  whatever is left of the adhesive. Neither measurement substitutes
  for the other, so the item disposition is the worse of the two.
- Position is a radial question. A feed-through is round and its
  tolerance is a circle around the drawing centre, so the offset is
  the root-sum-square of the two axis errors. Reading the larger axis
  error alone understates a diagonal miss by up to a factor of root
  two and quietly accepts a part that is outside the circle.
- Bond coverage is a minimum, not an allowance. It is the bonded
  footprint over the footprint the drawing calls for, and it fails
  downward. Everything else in the screen fails upward.
- The released perimeter is a second and independent bond question.
  Coverage can look healthy while the bond line has opened around one
  side, and once the release passes the rework fraction the coverage
  figure stops describing anything load-bearing.
- Where a feed-through sits changes its allowances. The core interface
  and the harness exit margin carry tightened offset and area limits,
  because a displaced passage there lands on the feature the panel was
  built around.
- A short list is decided by presence alone: a feed-through free to
  move, a substrate cracked at the passage, and a feed-through fitted
  where the drawing drew no passage. There is no size below which
  those pass, so measuring them more carefully cannot change the call.
- A drawing feed-through with no inspection record is not a clean
  feed-through. The panel is held at reject until every passage the
  drawing calls out has been looked at and written down.

## Workflow

1. Open the panel record against a panel identifier and take the list
   of feed-throughs the assembly drawing calls out. A survey with no
   traceable identifier cannot be dispositioned.
2. For each feed-through, take the measured centre against the drawing
   centre as a radial offset and disposition it against the
   zone-scaled accept and rework tolerances.
3. Take the bonded footprint against the required footprint as a
   coverage fraction and disposition it against the coverage minimum
   and the rework floor. Do not scale a minimum by the zone factor.
4. Take the released run against the whole bond perimeter as a
   fraction and disposition it against the accept and rework
   fractions. Keep it separate from the coverage call.
5. Categorize any further indication by kind and zone, route the
   not-tolerated kinds to a presence decision and the graded ones to
   the zone-scaled area limits.
6. Roll the legs into the feed-through disposition, taking the worst,
   and record which leg drove it.
7. Close with the panel verdict, the not-tolerated feed-throughs
   listed apart, any drawing passage still without a record, any
   feed-through found with no passage drawn for it, and the
   re-inspection duty a rework creates.

## Pitfalls

- Taking the larger axis error as the position offset. The tolerance
  is a circle, the measurement is a root-sum-square, and a diagonal
  miss inside both axis limits can still sit outside the circle.
- Scaling the coverage minimum by the zone factor. A factor below one
  tightens an allowance but loosens a minimum, so applying it to
  coverage accepts a thinner bond exactly where the zone was meant to
  demand a better one.
- Treating coverage and released perimeter as one number. A bond can
  hold most of its area while one side has opened, and averaging the
  two hides the release that is about to take the rest.
- Reading an accepted bond as an accepted feed-through. Position is a
  separate leg and a well-bonded part in the wrong hole still fails.
- Counting a drawing feed-through with no record as clean. An absent
  record is not an absent defect; it is an unexamined passage, and it
  holds the panel open.
- Comparing a measurement with a scaled limit by bare arithmetic. The
  limit is a product of a criteria value and a zone factor and the
  offset is a square root, so a value exactly on the limit can
  evaluate a few units in the last place above it; the comparison
  absorbs that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The radial offset, the bond coverage fraction, the released perimeter
fraction, the zone-scaled allowances, the presence-decided conditions,
the unrecorded and undrawn reconciliation and the panel rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_feed_through_visual_inspection.py against
scripts/e2008_feed_through_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_feed_through_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
