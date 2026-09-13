---
name: e20-passive-intermodulation-acceptance-levels
description: "Use when determine the passive-intermodulation interference a development may present to a victim receive-chain under ECSS-E-ST-20C clause 7.4.2 and agree it with the customer: convert each victim band's receiver-noise-floor and permitted interference-to-noise-ratio into a tolerable interference level, refer that level to the transmit antenna port through the antenna-port-isolation, subtract the measurement-uncertainty and the design-margin, reconcile the supplier-proposed level against the customer-required level, and bind the agreed level to the carrier-plan (carrier count, carrier-power, carrier frequencies) it was derived for. Trigger: ecss, e-st-20-electrical-scope, passive-intermodulation, pim-acceptance-level, customer-agreed-interference, receiver-noise-floor, interference-to-noise-ratio, antenna-port-isolation, carrier-plan."
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
  tags: [ecss, e-st-20-electrical-scope, e20-passive-intermodulation-acceptance-levels, passive-intermodulation, pim-acceptance-level, customer-agreed-interference, receiver-noise-floor, interference-to-noise-ratio, antenna-port-isolation, carrier-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Passive-Intermodulation Acceptance Levels (space-systems/ecss/e20-passive-intermodulation-acceptance-levels)

Use when the task is the ECSS-E-ST-20C clause 7.4.2 activity of agreeing
with the customer, during development, how much passive-intermodulation
interference the transmit-chain is allowed to deliver into each victim
receive-chain -- deriving that number from the victim's own sensitivity
rather than quoting a habitual catalogue figure, and recording the
carrier-plan the number is only valid for.

## Domain quick reference

- Passive-intermodulation arises when two or more transmit carriers
  share a non-linear passive junction (a contact, a coating, a
  waveguide flange, a corroded braid). The mixing products land at
  integer-combination frequencies; the odd-order products whose
  coefficient sum is one sit near the carriers and therefore near the
  co-located receive-band, which is what makes them a system problem
  rather than a component curiosity.
- The acceptance-level is a derived quantity, not a preference. It
  starts at the victim receiver-noise-floor, is raised by the permitted
  interference-to-noise-ratio (a negative dB allowance -- the agreed
  desensitisation the link-budget can absorb), giving the tolerable
  interference at the receiver input. Referring it back to the transmit
  antenna port adds the antenna-port-isolation between the two ports,
  then subtracts the measurement-uncertainty of the intended
  verification bench and the design-margin held for flight-model
  degradation, so the number handed to the hardware is the one that can
  actually be demonstrated.
- An acceptance-level is meaningless without the carrier-plan it was
  derived for. Passive-intermodulation grows steeply with carrier-power
  and with carrier count, so an agreed level is bound to a declared
  carrier count, a declared per-carrier-power and a declared transmit
  frequency span. An as-flown plan that adds carriers, raises the
  per-carrier-power or moves carriers outside the declared span
  invalidates the agreement and forces a re-derivation.
- Supplier-proposed and customer-required levels rarely coincide. The
  stricter of the two governs; a supplier level above the customer
  requirement but inside the agreed negotiation band is negotiable,
  and one beyond it needs a formal waiver -- it is never silently
  adopted.
- Several products can fall in one victim band. They combine as powers,
  not as dB, so the aggregate is the power-sum of the contributions and
  it is the aggregate, not the worst single product, that is compared
  against the acceptance-level.

## Workflow

1. Capture every victim band: identifier, band edges, receiver
   noise-floor, permitted interference-to-noise-ratio, and the
   antenna-port-isolation from the transmit port to that receiver.
   Reject a band with inverted or non-positive edges, a non-finite
   noise-floor, a positive interference-to-noise allowance, or a
   negative isolation before it enters the derivation.
2. Compute the tolerable interference at each victim receiver input as
   noise-floor plus the interference-to-noise allowance.
3. Refer it to the transmit antenna port: add the antenna-port-isolation,
   then subtract the verification measurement-uncertainty and the
   design-margin. The result is the derived acceptance-level for that
   victim band.
4. Validate the carrier-plan: at least two carriers, distinct positive
   frequencies, finite per-carrier-power. Record the carrier count, the
   power-sum of the carriers and the transmit frequency span; the
   agreement is issued against exactly this plan.
5. Reconcile per band: compare the supplier-proposed level against the
   derived customer-required level. Mark it agreed when the supplier
   level is at or below the requirement, negotiable when it exceeds it
   by no more than the agreed negotiation band, and waiver-required
   beyond that. The agreed level is the stricter of the two.
6. Re-check an as-flown carrier-plan against the recorded plan: more
   carriers, higher aggregate carrier-power, or a carrier outside the
   declared transmit span each raise a finding that voids the agreement.
7. Aggregate: the band is agreed only when its reconciliation status is
   agreed, the power-sum of its expected products sits at or below the
   agreed level, and no carrier-plan finding is open.

## Pitfalls

- Quoting a habitual catalogue level (a familiar dBm figure) instead of
  deriving it from the victim receiver-noise-floor -- the same hardware
  can be generous for one payload and an outright violation for another.
- Comparing the derived level at the wrong reference plane: an
  acceptance-level at the transmit antenna port and one at the receiver
  input differ by the whole antenna-port-isolation, and swapping them
  moves the requirement by tens of dB in the flattering direction.
- Folding the measurement-uncertainty in with the wrong sign, so the
  agreed number is one the verification bench can never demonstrate.
- Comparing only the worst single product against the acceptance-level
  when several products land in the same victim band -- contributions
  add as powers, and two products of equal level sit 3 dB above either.
- Treating an agreed level as plan-independent and letting the as-flown
  carrier-plan grow -- the agreement was issued against a declared
  carrier count and per-carrier-power, and it lapses when either moves.
- Reading a supplier level that merely sits inside the negotiation band
  as an agreement; it is an open negotiation until the customer records
  a decision, and beyond the band it is a waiver, not a pass.

## Behavior contract (gate 3)

The tolerable-interference derivation, the reference-plane transfer,
the carrier-plan validation, the supplier/customer reconciliation and
the power-sum aggregation are exercised by the gate 3 contract test:
`scripts/test_e20_passive_intermodulation_acceptance_levels.py` against
`scripts/e20_passive_intermodulation_acceptance_levels_logic.py`
(stdlib unittest, offline, deterministic). Run:
python3 scripts/test_e20_passive_intermodulation_acceptance_levels.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
