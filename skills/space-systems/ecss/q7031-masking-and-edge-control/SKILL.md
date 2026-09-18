---
name: q7031-masking-and-edge-control
description: "Size the overspray halo of a spray set-up from gun stand-off and fan angle under ECSS-Q-ST-70-31C, turn it into the masking margin each keep-out zone earns from its category, and grade every declared mask footprint against that margin; then evaluate edge coverage separately, deriving the film a convex edge retains from its radius and the number of stripe coats a sharp edge needs to reach its minimum. Use when a masking plan, a keep-out clearance or an edge coverage requirement has to be settled before the gun is triggered. Trigger: ecss, q-st-70-31c-paint-application, coating-overspray-halo-containment, paint-masking-keep-out-margin, coating-edge-retention-factor, coating-stripe-coat-count, paint-keep-out-zone-criticality."
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
  tags: [ecss, q-st-70-31c-paint-application-scope, q7031-masking-and-edge-control, coating-overspray-halo-containment, paint-masking-keep-out-margin, coating-edge-retention-factor, coating-stripe-coat-count, paint-keep-out-zone-criticality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Masking and Edge Control (space-systems/ecss/q7031-masking-and-edge-control)

Use when the task is the masking and coverage control of ECSS-Q-ST-70-31C:
deciding how far a mask has to stand off each surface that must stay bare,
and deciding whether the edges and corners of the part will actually hold the
film the requirement asks for.

## Domain quick reference

- Atomised paint does not stop at the pattern. The aimed fan has a half-width
  set by stand-off and fan angle, and a drifting fraction lands outside it, so
  the containment question is about a halo radius rather than about where the
  operator points the gun.
- Keep-out zones do not all earn the same clearance. An optical surface, a
  bonding or electrical contact face, a sealing land and a plain structural
  area carry very different consequences for a stray droplet, so the required
  margin is the halo scaled by the zone's category.
- A convex edge holds less film than the flat beside it. Surface tension
  pulls the wet film away from the edge as it levels, so retained thickness
  rises with edge radius from a sharp-edge floor toward the flat value and
  never quite reaches it. This is why edges are the first place a coating
  system loses its barrier.
- The remedy for a thin edge is a stripe coat applied before or between the
  full coats, and the number of stripe coats is derivable: it is how many
  extra passes of the same retained thickness close the deficit to the edge
  minimum.
- Masking is also a removal problem. A mask that meets the margin but cannot
  be lifted without tearing a cured film, or that is left on through a bake
  it was not qualified for, trades an overspray finding for an edge-damage
  one.

## Workflow

1. Validate the spray set-up: a positive stand-off, a fan angle strictly
   between the degenerate and the straight case, and a drift fraction that is
   not negative.
2. Size the overspray halo from stand-off and fan angle, inflated by the
   drift fraction declared for the gun and material.
3. For each keep-out zone, look up its category multiplier, form the required
   margin and compare it with the mask footprint actually drawn. Reject a
   duplicate zone name rather than silently grading one of them twice.
4. Where edge features are declared, derive the retention factor from each
   edge radius, convert it to a retained dry film thickness at the nominal
   coat thickness, and compare with the edge minimum.
5. Where an edge misses its minimum, derive the stripe-coat count that closes
   the deficit instead of reporting a bare shortfall.
6. Return one containment verdict with the halo, the per-zone records, the
   per-edge records and every finding named.

## Pitfalls

- Sizing the mask from the visible pattern. The pattern edge is where the
  bulk lands, not where the material stops; the drift fraction is the part
  that reaches the keep-out zone.
- Giving every zone the same margin. A margin adequate for a structural panel
  is not adequate for an optical face, and a single blanket number is either
  wasteful everywhere or short where it matters.
- Reading an edge as a flat. A gauge reading taken on the flat next to a
  corner does not describe the corner, and the coating system's barrier
  performance is set by its thinnest continuous point.
- Adding stripe coats without re-checking the flats. Stripe coats build local
  thickness, and a stripe applied over the full coat can push the adjacent
  flat past its own maximum.
- Shaving a required margin to fit a mask that is already cut. The required
  margin follows from the set-up; the way to reduce it is to change stand-off,
  fan angle or drift, not to change the requirement.

## Behavior contract (gate 3)

The set-up validation, halo sizing, category multiplier lookup, per-zone
margin grading, duplicate-zone rejection, edge retention factor, retained
edge thickness and stripe-coat derivation are exercised by the gate 3
contract test:
scripts/test_q7031_masking_and_edge_control.py against
scripts/q7031_masking_and_edge_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_masking_and_edge_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
