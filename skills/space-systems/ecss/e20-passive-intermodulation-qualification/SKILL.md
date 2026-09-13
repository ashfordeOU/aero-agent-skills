---
name: e20-passive-intermodulation-qualification
description: "Use when verify that every passive-intermodulation product raised by a spacecraft transmit carrier-plan stays under its allowable level inside an own receive-band or a third-party protected-band, per ECSS-E-ST-20C clause 7.4.5: enumerate the mixing products of the carrier-plan up to a chosen order, keep the ones whose frequency lands inside a protected-band, predict each product level from a measured passive-intermodulation reference using the per-carrier order coefficients and the order roll-off, compare it against the band interference-limit, and derive the qualification carrier-level and dwell-duration that envelope the flight carrier-plan. Trigger: ecss, e-st-20-electrical-scope, passive-intermodulation, intermodulation-product, receive-band-protection, protected-band-interference, carrier-plan, pim-qualification-level, order-coefficient."
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
  tags: [ecss, e-st-20-electrical-scope, e20-passive-intermodulation-qualification, passive-intermodulation, intermodulation-product, receive-band-protection, carrier-plan, pim-qualification-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS RF Systems — Passive-Intermodulation Qualification (space-systems/ecss/e20-passive-intermodulation-qualification)

Use when the task is the passive-intermodulation qualification of
ECSS-E-ST-20C clause 7.4.5 -- showing that each mixing product of the
transmit carrier-plan stays below the allowable level inside every own
receive-band and every third-party protected-band, and fixing the
qualification carrier-level and dwell-duration that envelope flight.

## Domain quick reference

- A passive-intermodulation product is a mixing product generated in a
  passive, non-linear junction (a metal-to-metal contact, a corroded
  interface, a loose waveguide flange, a ferromagnetic inclusion)
  driven by two or more transmit carriers. Its frequency is the integer
  combination sum(m_i * f_i) over the carrier-plan; its order is
  sum(|m_i|). Only odd orders fall close enough to the transmit
  carrier-plan to reach a co-located receive-band, so the odd orders
  (3, 5, 7, ...) are the ones enumerated; the even orders sit far out
  of band and are filtered.
- A product only matters where it lands. The two families of victim
  band are the own receive-band (the spacecraft's own receive chain,
  where the allowable level is set by the receiver noise-floor plus
  the agreed degradation allowance) and the third-party
  protected-band (a neighbouring service, where the allowable level
  comes from a coordination or regulatory interference-limit). A
  product outside every declared band is dropped -- it is real, but it
  is not a finding of this clause.
- The predicted product level is anchored on a measured
  passive-intermodulation reference: the level observed at a stated
  per-carrier reference level for a stated reference order. Scaling to
  the flight carrier-plan adds |m_i| dB of level change per dB of
  level change on carrier i, and removes a roll-off allowance for each
  order step above the reference order. The level arriving at the
  victim port is further reduced by the isolation between the
  generating junction and that port.
- Qualification bounds flight: the carriers are driven at the nominal
  per-carrier level raised by a qualification-margin, for a declared
  dwell-duration, so that the flight carrier-plan sits inside the
  demonstrated envelope rather than at its edge.

## Workflow

1. Capture the carrier-plan: every transmit carrier with an identifier,
   a positive frequency and a per-carrier level. Reject a duplicate
   identifier, a non-positive frequency or a non-finite level before
   anything is enumerated. Fewer than two carriers cannot mix, which
   is a rejected input, not an empty result.
2. Enumerate the mixing products up to the chosen maximum order: all
   integer coefficient vectors whose absolute sum equals an odd order
   from three upward, keeping only the combinations that land at a
   positive frequency.
3. Retain the products whose frequency falls inside a declared
   receive-band or third-party protected-band; discard the rest.
4. Predict each retained product level from the measured reference by
   applying the per-carrier order coefficients and the order roll-off,
   then subtract the isolation declared for that victim band.
5. Compare the arriving level against the band interference-limit and
   record the margin. A margin that is zero to within the level
   tolerance is compliant -- do not let the floating-point sum of
   several level terms turn an exactly-met limit into a violation.
6. Derive the qualification carrier-level (nominal plus the
   qualification-margin, per carrier) and the composite level of the
   qualification carrier-plan, together with the dwell-duration, and
   record them as the envelope the flight carrier-plan must sit inside.

## Pitfalls

- Enumerating only the two-carrier third-order combination. A three
  carrier plan raises three-carrier products of the same order that
  land somewhere else entirely, and the fifth and seventh orders reach
  bands the third order never touches.
- Treating the reference level as the flight level. The reference is
  tied to the per-carrier level at which it was measured; scaling it
  with the order coefficients is what makes it a prediction rather
  than a quotation.
- Comparing the generated level directly against the band limit and
  ignoring the isolation between the generating junction and the
  victim port -- that overstates every finding and hides which
  junctions actually drive the design.
- Reading "no product in band" as compliant when no band was declared.
  An empty band list means the receive-band and coordination inputs
  were never captured, which is itself a finding.
- Qualifying at the nominal carrier-level. Without the
  qualification-margin the flight carrier-plan sits at the edge of the
  demonstrated envelope, so any in-orbit level growth is unverified.

## Behavior contract (gate 3)

The carrier-plan validation, product enumeration, band-mapping, level
prediction, margin evaluation and qualification-envelope logic is
exercised by the gate 3 contract test:
scripts/test_e20_passive_intermodulation_qualification.py against
scripts/e20_passive_intermodulation_qualification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_passive_intermodulation_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
