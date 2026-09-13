---
name: e2006-secondary-arc-test-characteristics
description: "Use when verify that a secondary-arc campaign on array coupon samples is laid out and graded as ECSS-E-ST-20-06C clause 7.2.3.2 requires: check each coupon against the flight article for conductor-gap, coverglass-thickness, interconnect-type, adhesive-type, harness-routing and string-count representativeness, lay out the voltage-by-current campaign matrix, size the triggered primary-arc budget per point with a doubled count inside the band around the expected sustained-arc boundary, categorize each recorded event as below-detection, non-sustained, temporary-sustained or permanent-sustained from its duration and current, and grade the campaign. Trigger: ecss, e-st-20-06c, secondary-arc-campaign, array-coupon-sample, coupon-representativeness, sustained-arc-detection, primary-arc-trigger, arc-test-matrix, arc-event-duration, solar-array-arcing."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-secondary-arc-test-characteristics, e-st-20-06c, secondary-arc-campaign, array-coupon-sample, coupon-representativeness, sustained-arc-detection, primary-arc-trigger, arc-test-matrix]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Secondary-Arc Test Characteristics (space-systems/ecss/e2006-secondary-arc-test-characteristics)

Use when the task is the clause 7.2.3.2 provisions of ECSS-E-ST-20-06C on
how array coupon samples are used in a secondary-arc verification
campaign: what the coupon has to reproduce, how the test points are spread
over generator voltage and current, how many primary arcs each point is
driven through, and what counts as a sustained arc in the record.

## Domain quick reference

- A coupon stands in for the flight array only to the extent that it
  reproduces the arc site. The parameters that matter are the gap between
  adjacent conductors, the coverglass thickness, the interconnect and
  adhesive types and the harness routing behind the sample, plus enough
  strings and cells for a real string-to-string potential to exist across
  a gap. A coupon may carry more strings than the flight article, never
  fewer, and the dimensional parameters are held to a stated fraction of
  the flight values rather than an informal likeness.
- The campaign is a grid, not a single point. Each generator voltage is
  crossed with each available current so the sustained-arc boundary is
  approached from both axes; a single worst-case point cannot show where
  the boundary lies.
- Statistics come from repetition. Each matrix point is driven through a
  fixed number of triggered primary arcs, and points inside the band
  around the expected sustained-arc boundary carry a multiplied count
  because that is where the transition is resolved.
- A recorded event is categorized by two measurements. Below the current
  detection floor there is no arc to grade at all. Above it, an event that
  extinguishes inside the short-duration limit is non-sustained, one that
  persists past it but self-extinguishes is temporary-sustained, and one
  that persists past the long-duration limit is permanent-sustained. Both
  sustained categories are failures; only the non-sustained ones count as
  a clean triggered arc.
- A point passes when it reached its arc budget with no sustained event.
  The campaign passes when every coupon was representative, every point
  reached its budget, and no sustained event was recorded anywhere.

## Workflow

1. Record the flight article parameters that define the arc site and
   validate every coupon against the same schema. Reject a coupon with
   fewer than the minimum strings or cells, a non-positive dimension or a
   missing material name before the campaign is planned.
2. Compare each coupon with the flight article: dimensional parameters
   against the tolerance fraction, material and routing names for exact
   agreement, string count for at-least equality. Treat a relative
   deviation that lands a few bits above the tolerance as at the
   tolerance.
3. Lay out the matrix as the full grid of generator voltage points against
   current points, rejecting duplicates and values above the campaign
   ceilings.
4. Size the arc budget: a base count of triggered primary arcs per point,
   multiplied for points inside the band around the expected sustained-arc
   boundary, and summed to a campaign total.
5. Derive each event duration from its recorded start and end timestamps
   rather than a typed-in number, and categorize the event from the
   duration and the arc current against the detection floor.
6. Grade each point on two independent conditions: the triggered-arc count
   reached its budget, and no sustained event was recorded there.
7. Grade the campaign on the coupon findings and the point findings
   together, and report which coupons were unrepresentative, which points
   fell short of the budget and which points recorded a sustained arc.

## Pitfalls

- Testing one coupon and calling the matrix covered. The clause rests on
  repetition across samples; a single coupon cannot separate a site defect
  from a design property.
- Scaling a coupon down to fewer strings than the flight article. The
  string-to-string potential across the gap is the quantity under test,
  and a reduced sample quietly tests a lower voltage than flight.
- Sweeping voltage only. A sustained arc needs both potential and current,
  so a voltage-only sweep at one current never finds the boundary.
- Spending the same number of arcs everywhere. Points far from the
  boundary confirm what is already known; the doubled count belongs in the
  band where the transition actually happens.
- Counting an event below the current detection floor as a triggered arc.
  It inflates the count towards the budget while demonstrating nothing.
- Reading a temporary-sustained event as a pass because the arc
  self-extinguished. It persisted past the non-sustained limit, which is
  the behaviour the campaign exists to find.
- Failing an at-limit event because a timestamp difference or a relative
  deviation printed a hair over. The representation error belongs in the
  comparison, never in the campaign limit.

## Behavior contract (gate 3)

The coupon-validation, representativeness, matrix, arc-budget,
event-categorization, point-grading and campaign-grading logic is
exercised by the gate 3 contract test:
scripts/test_e2006_secondary_arc_test_characteristics.py against
scripts/e2006_secondary_arc_test_characteristics_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_secondary_arc_test_characteristics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
