---
name: e2007-external-ground-connection-provisions
description: "Use when verify the external-ground-connection-provisions that ECSS-E-ST-20-07C clause 4.2.11.3 requires for charge-equalization before a handling-or-mating operation: qualify each attachment point for its bond back to structure, its current-limiting bleed-resistance and its reachability in the configuration where it is used, then for every operation compute the resistance-capacitance decay of the item's stored potential, check the residual-potential after the planned dwell against the electrostatic-susceptibility threshold, check the peak equalization-current against the soft-ground limit, and derive the bleed-resistance window that satisfies both. Trigger: external-ground-connection-provisions, charge-equalization, soft-ground-bleed-resistance, residual-potential-decay, equalization-dwell-time, electrostatic-susceptibility-threshold, grounding-stud-provision, handling-and-mating-operations."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-external-ground-connection-provisions, charge-equalization, soft-ground-bleed-resistance, residual-potential-decay, equalization-dwell-time, electrostatic-susceptibility-threshold, grounding-stud-provision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility -- External Ground Connection Provisions (space-systems/ecss/e2007-external-ground-connection-provisions)

Use when the task is the charge-equalization provision of
ECSS-E-ST-20-07C clause 4.2.11.3 -- the attachment points that let an
external cable bring a spacecraft, an item of ground-support-equipment
or a handling fixture to a common potential before anyone touches or
mates it, and the dwell and bleed-resistance that make the equalization
real rather than nominal.

## Domain quick reference

- The provision is hardware on the vehicle: a grounding-stud, a
  banana-jack-receptacle or a clamp-lug, solidly bonded to structure
  and marked so an operator finds it without a drawing. Its own bond
  back to structure must sit inside a low-milliohm allowance (10
  milliohm here) -- a provision that is itself poorly bonded equalizes
  nothing.
- Equalization is a resistance-capacitance decay, not an event. The
  item's stored potential falls as V(t) = V0 x exp(-t / (R x C)), where
  R is the series bleed-resistance in the lead and C the item's
  capacitance to its surroundings. The dwell is what turns a touched
  stud into an equalized item.
- Both ends of R are constrained, which is why the provision has to be
  sized rather than picked. Too little resistance and the initial
  equalization-current V0/R is a discharge through the very hardware
  being protected; too much and the decay is slower than the time the
  operation allows. The acceptable window is R >= V0 / I_limit and
  R <= t_available / (C x ln(V0 / V_target)); a soft-ground lead
  typically lands near one megaohm.
- The residual target comes from the item's electrostatic-susceptibility
  category -- withstand 250 V for category-0, 500 V for category-1a,
  1000 V for category-1b, 2000 V for category-2 -- derated to a tenth
  of the withstand so the residual is not sitting at the limit when the
  operator makes contact.
- A provision is only usable in the configuration where it is reachable.
  A stud under an already-mated fairing is not a provision for the
  mating operation, whatever the drawing says.

## Workflow

1. Qualify each provision independently of any operation: recognised
   attachment style, bond-to-structure inside the milliohm allowance, a
   current-limiting bleed-resistance in the lead rather than a hard
   short, and a marking. Reject an unrecognised style, a negative
   resistance and a missing identifier as input defects.
2. For each handling-or-mating operation, resolve the provision it
   names. A named provision that is not in the catalogue is an input
   defect -- never silently substitute a nearby stud.
3. Check reachability: the operation's configuration must appear in the
   provision's reachable set.
4. Compute the time constant R x C, then the residual-potential after
   the planned dwell, and compare it with a tenth of the withstand
   voltage for the item's susceptibility category.
5. Compute the peak equalization-current V0 / R and compare it with the
   soft-ground current limit. Report it even when it passes; it is the
   number that decides whether the bleed-resistance may be lowered to
   buy dwell time.
6. Derive the bleed-resistance window from the current limit and the
   available dwell. Report the window as infeasible when its lower
   bound exceeds its upper bound -- that means no resistor value can
   satisfy both constraints and the dwell or the initial potential has
   to change instead.
7. Aggregate per provision and per operation; the provision set is
   compliant only when both finding lists are empty.

## Pitfalls

- Treating contact with the stud as equalization. Without the dwell
  the item is connected, not equalized, and the residual can still be
  hundreds of volts when the connector mates.
- Bonding the lead straight to structure with no bleed-resistance. The
  equalization then happens as a single discharge through the item,
  which is the event the provision exists to prevent.
- Sizing the bleed-resistance from the current limit alone. That fixes
  only the lower bound; the upper bound comes from the dwell the
  operation can actually hold, and a one-sided size can be an order of
  magnitude too large.
- Comparing the residual with the withstand voltage itself. The
  residual is derated to a fraction of the withstand precisely so the
  item is not at its limit at the moment of contact.
- Widening the residual threshold because a dwell set exactly at the
  computed requirement lands a hair above it. An exponential decay
  evaluated at a logarithm-derived dwell overshoots in the last place
  -- absorb that in the comparison tolerance, never by relaxing the
  threshold or shortening the required dwell.

## Behavior contract (gate 3)

The provision-qualification, decay, residual-potential, peak-current,
resistance-window and aggregate logic is exercised by the gate 3
contract test:
`scripts/test_e2007_external_ground_connection_provisions.py` against
`scripts/e2007_external_ground_connection_provisions_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_external_ground_connection_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
