---
name: e20-equipment-test-point-accessibility
description: "Use when verify that the stimulus and measurement points of a space electrical equipment item meet ECSS-E-ST-20C clause 4.2.4: categorize each access provision as non-intrusive (dedicated test connector, buffered monitor pin, breakout box) or intrusive (connector demate, wire splice, solder-lug tap), flag any provision that alters the electrical configuration of the unit under test, compute the instrument loading error from source and input impedance and derive the input impedance the allowable demands, grade series isolation against node criticality, and confirm every signal the verification plan needs maps to a reachable point. Trigger: ecss, e-st-20-electrical-scope, test-point-accessibility, stimulus-injection-point, non-intrusive-probing, instrument-loading-error, test-connector-provision, series-isolation-resistor, electrical-configuration-integrity, unit-under-test."
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
  tags: [ecss, e-st-20-electrical-scope, e20-equipment-test-point-accessibility, test-point-accessibility, stimulus-injection-point, non-intrusive-probing, instrument-loading-error, series-isolation-resistor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Equipment Test Point Accessibility (space-systems/ecss/e20-equipment-test-point-accessibility)

Use when the task is the accessibility review of ECSS-E-ST-20C clause
4.2.4 -- checking that every stimulus and measurement point needed to
verify an equipment item can be driven or observed without changing the
electrical configuration of the unit under test, that the probing
instrument does not load the node beyond its allowable, and that the
test interface cannot propagate a fault inward.

## Domain quick reference

- Clause 4.2.4 is an accessibility requirement with a hard qualifier:
  the point has to be reachable *and* reaching it must leave the flight
  electrical configuration intact. Access provisions therefore split
  into two families. Non-intrusive: a dedicated test connector, a
  buffered monitor pin brought out for the purpose, a harness breakout
  box inserted at a defined interface, a bench test adapter. Intrusive:
  demating a flight connector, cutting or splicing a wire, tapping a
  solder lug, lifting a board-level component to get a probe on a net.
  An intrusive provision means the configuration measured is not the
  configuration flown, so the measurement characterizes something other
  than the deliverable.
- Reaching a node is not the same as measuring it. A probing instrument
  of input impedance Zin placed on a node of source impedance Zs forms
  a divider, and the fractional measurement error is
  100 x Zs / (Zs + Zin) percent. The same expression inverts: for an
  allowable error e, the instrument needs at least
  Zs x (100 - e) / e of input impedance. A high-impedance node behind a
  modest probe is the classic case where the point is "accessible" and
  the number coming off it is still wrong.
- The test interface is also a fault path in the inward direction. A
  point that lands on a node whose loss would hurt the mission needs a
  series isolation element sized by that consequence, so a short,
  overvoltage or miswire on the ground-support side cannot reach the
  flight node. Routine nodes need none; a mission-critical node needs a
  meaningful series resistance; a node with catastrophic consequence
  needs an order more.
- Accessibility is judged against the verification plan, not against
  the connector drawing. Every stimulus the plan injects and every
  signal it measures must map to at least one point that is both
  non-intrusive and reachable in the integrated configuration; a signal
  whose only route is an intrusive provision, or a point behind a
  flight connector that must first be demated, is an uncovered signal.

## Workflow

1. List every test point the design provides and, for each, record the
   access provision, the signals it carries, the node criticality, the
   source impedance, the instrument input impedance the test setup
   brings, the allowable loading error and the series isolation fitted.
   Reject an unrecognized access provision before it enters the review.
2. Categorize each provision as non-intrusive or intrusive. Flag every
   intrusive provision as altering the electrical configuration of the
   unit under test, and flag separately any point -- intrusive or not
   -- that can only be reached by demating a flight connector.
3. Compute the loading error for each point from the source and
   instrument input impedances and compare it against the allowable.
   Where it is exceeded, report the minimum input impedance that would
   have met the allowable so the finding carries its own fix.
4. Grade the fitted series isolation against the minimum set by the
   node's criticality and flag any point that observes a
   mission-critical or higher node through insufficient isolation.
5. Take the stimulus and measurement signals the verification plan
   requires and subtract those covered by non-intrusive, non-demate
   points; anything left is a signal with no accessible point and is a
   clause 4.2.4 finding against the equipment, not against a point.
6. Aggregate per point and per equipment item. The equipment is not
   accessible-by-design until every point's access, loading and
   isolation lists are empty and the coverage list is empty too.

## Pitfalls

- Accepting an intrusive provision because the measurement it yields
  looks right -- the finding is the configuration change itself, and a
  correct number taken from a demated or spliced unit is evidence about
  a configuration that will not fly.
- Treating presence of a test connector as accessibility. A point that
  exists but sits behind a flight connector that must be demated to
  reach it fails the same clause, and the coverage step is where that
  surfaces; a connector-level inventory alone never sees it.
- Reporting a loading exceedance without the required input impedance.
  The divider inverts exactly, so the fix is computable; leaving it out
  turns a closed finding into an open action.
- Sizing series isolation by what fits on the board rather than by the
  consequence of a fault propagating inward from ground support
  equipment -- the isolation minimum is set by the node's criticality,
  and a routine-node value on a mission-critical node reads as a pass
  in any check that does not carry the criticality alongside.
- Reading an empty finding list on every point as compliance while the
  verification plan still names a signal nothing reaches. Point-level
  greens and equipment-level coverage are separate verdicts.

## Behavior contract (gate 3)

The access categorization, loading-error and required-impedance
accounting, series-isolation grading, stimulus-coverage and aggregated
review logic is exercised by the gate 3 contract test:
scripts/test_e20_equipment_test_point_accessibility.py against
scripts/e20_equipment_test_point_accessibility_logic.py (stdlib
unittest, offline). Run:
`python3 scripts/test_e20_equipment_test_point_accessibility.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
