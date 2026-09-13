---
name: e2006-internal-metal-grounding-paths
description: "Use when verify that every internal metallic item of a spacecraft -- harness-shield, equipment-enclosure, connector-backshell, internal-bracket, secondary-structure -- carries two independent grounding routes under ECSS-E-ST-20-06C clause 9.2.2: categorize each internal-metallic-item into its bonding family, build every candidate grounding-route from its bond segments, total the segment bond-resistance and check it against the family route cap, then prove two surviving routes are genuinely independent by showing they share no bond segment and no intermediate tie-point, so one broken strap cannot leave the item floating. Flags single-route items, shared-segment pseudo-redundancy and over-resistance routes. Trigger: ecss, e-st-20-electrical-scope, internal-metallic-item, dual-grounding-route, bond-strap-independence, grounding-route-resistance, shared-tie-point, internal-electrostatic-discharge, e-st-20-06c-clause-9-2-2."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-internal-metal-grounding-paths, internal-metallic-item, dual-grounding-route, bond-strap-independence, grounding-route-resistance, shared-tie-point]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design -- Internal Metallic Item Grounding Routes (space-systems/ecss/e2006-internal-metal-grounding-paths)

Use when the task is the clause 9.2.2 check of ECSS-E-ST-20-06C: every
metallic item inside the spacecraft -- harness-shield, overbraid,
equipment-enclosure, connector-backshell, internal-bracket, secondary
structure -- is tied to the grounding reference by two grounding routes
that are independent of each other, and each route is low-resistance
enough to hold the item at reference potential.

## Domain quick reference

- The clause is an internal-electrostatic-discharge control, not a
  bonding-resistance nicety. An internal metallic item that loses its
  only tie floats, charges from penetrating radiation, and eventually
  discharges into whatever harness runs past it. Two routes exist so
  that the loss of one strap, one backshell termination or one
  pigtail is a maintenance finding rather than a floating conductor.
- A grounding-route is an ordered chain of bond segments (strap,
  pigtail, backshell termination, fastener bond, structural weld)
  running from the item to the grounding reference. Its resistance is
  the sum of its segment resistances; a route whose total exceeds the
  cap for the item family is not a usable route and must not be
  counted toward the required two.
- Independence is the part most often faked. Two routes leaving the
  same item are independent only when they share no bond segment AND
  no intermediate tie-point -- the node they pass through on the way
  to the reference. Two straps that both land on one common bracket
  before reaching structure are a single route drawn twice: the
  bracket bond is a shared single point of failure, so the item is
  singly grounded no matter how many straps are on the drawing.
- Route caps differ by family. Shield and enclosure terminations are
  held to a tighter total than a bolted structural bond, because the
  shield path also carries the radio-frequency return; an item whose
  family is not recognized has no cap on record and is rejected rather
  than assessed against a guessed number.
- The grounding reference itself (structure ground, chassis reference)
  is the common endpoint of every route and is not counted as a shared
  tie-point -- independence is about everything strictly between the
  item and that reference.

## Workflow

1. Inventory every internal metallic item and categorize it into its
   bonding family (shield, enclosure, structure). Reject an
   unrecognized item kind before it enters the assessment rather than
   defaulting it to the loosest cap.
2. For each item, build every candidate grounding-route from its bond
   segments. Reject a route with no segments, a repeated segment, a
   negative resistance or a duplicate route identifier.
3. Total each route's resistance by summing its segment resistances,
   and compare the total with the family route cap. A total sitting
   exactly on the cap is compliant; absorb the floating-point
   representation error of the sum in the comparison rather than
   widening the cap.
4. Discard the over-resistance routes, then search the surviving
   routes for the largest mutually independent subset -- every pair in
   the subset sharing no bond segment and no intermediate tie-point.
5. Compare that subset size with the required two. Report the item as
   singly grounded when only one independent route survives, and as
   ungrounded when none does.
6. Aggregate per item: the item is clause 9.2.2 compliant only when
   two independent routes survive the resistance screen. Roll the
   findings up into a campaign verdict that is compliant only when
   every item's finding list is empty.

## Pitfalls

- Counting straps instead of independent routes -- three straps that
  all terminate on one common bracket give one route, and the drawing
  will happily show three. Independence is tested on the tie-points,
  not the strap count.
- Counting an over-resistance route toward the required two. Screen
  each route against its family cap first, then test independence on
  the survivors; doing it in the other order lets a dead route supply
  the redundancy.
- Applying the tighter shield cap to a bolted structural bond, or the
  looser structural cap to a backshell termination -- the family sets
  the cap, and an unrecognized family means the cap was never
  captured, which is a finding rather than a pass.
- Treating a route total that lands a few units in the last place over
  the cap as a violation. The total is a sum of floats; a physically
  compliant route must stay compliant, so the comparison absorbs the
  representation error while the engineering cap stays untouched.
- Counting the grounding reference as a shared tie-point and
  concluding no two routes can ever be independent -- every route ends
  there by definition.

## Behavior contract (gate 3)

The item categorization, route construction, resistance screening,
independence search and per-item verdict logic is exercised by the
gate 3 contract test:
scripts/test_e2006_internal_metal_grounding_paths.py against
scripts/e2006_internal_metal_grounding_paths_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2006_internal_metal_grounding_paths.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
