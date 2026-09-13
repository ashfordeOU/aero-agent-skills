---
name: e2006-common-charging-engineering-concerns
description: "Use when assess the spacecraft-charging concerns a hardware item actually carries under ECSS-E-ST-20-06C clause 4.1.2: compute the differential-potential between an external-surface and its structure reference and against an adjacent surface, compare both and the absolute frame potential with electrostatic-discharge-onset thresholds, derive the bulk electric-field a deposited current density drives through a dielectric from its resistivity, check that field and the deposition rate against buried-charge-breakdown limits, flag an ungrounded or high-impedance-bonded conductor, and rank every finding by severity. Trigger: ecss, e-st-20-electrical-scope, e2006-common-charging-engineering-concerns, surface-charge-buildup, internal-charge-deposition, differential-potential-esd, buried-charge-breakdown, dielectric-bulk-field, floating-conductor-bonding."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-common-charging-engineering-concerns, surface-charge-buildup, internal-charge-deposition, differential-potential-esd, buried-charge-breakdown, dielectric-bulk-field, floating-conductor-bonding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Common Charging Engineering Concerns (space-systems/ecss/e2006-common-charging-engineering-concerns)

Use when the task is the item-level concern list of ECSS-E-ST-20-06C
clause 4.1.2 -- the two effects that recur on every charging-exposed
design, surface-charge-buildup and internal-charge-deposition, plus the
bonding gaps that turn either of them into a discharge. The ambient
environment that drives them is a separate leaf; this one takes an
item's own numbers and returns its concerns ranked by severity.

## Domain quick reference

- Surface-charge-buildup shows up as two different numbers. The absolute
  frame potential is what the whole conductive structure floats to
  relative to the ambient plasma; it stresses ground-referenced
  interfaces but on its own it does not arc. The differential potential
  -- between a dielectric surface and the structure behind it, or
  between two adjacent surfaces that charge at different rates -- is what
  actually breaks down, and its onset threshold is far lower than the
  absolute one. An item is evaluated against both, with the differential
  finding carrying the higher severity.
- Internal-charge-deposition is a bulk effect, not a surface one. Charge
  that penetrates the outer skin is stored inside a dielectric and bleeds
  away through its own conduction; in steady state the electric-field it
  sustains is the deposited current density times the bulk resistivity.
  That field is compared against the dielectric strength reduced by a
  safety factor, and a field above the reduced allowable is a
  buried-charge-breakdown concern.
- The deposition rate is screened independently of the field. A
  current density into the dielectric below the screening limit is
  considered benign whatever the resistivity, and a rate above it is a
  concern even when the field check happens to pass -- the two are not
  substitutes for each other. Shield thickness is the third leg: a
  dielectric behind less than the guideline aluminium-equivalent
  thickness is flagged for review.
- A conductor that is not bonded to the structure floats free and
  accumulates charge with no bleed path, which is the classic
  discharge source; a conductor bonded through an unexpectedly high
  resistance behaves like a slow version of the same problem. Both are
  checked from the item's bonding record, not inferred from its material.
- Every threshold comparison absorbs floating-point representation error.
  A potential difference or a resistivity-times-current-density product
  that lands a few units in the last place above a limit it physically
  meets is treated as compliant; the limit itself is never widened.

## Workflow

1. Normalise the item: name, kind (external-surface, buried-dielectric or
   floating-conductor) and the fields that kind requires. Reject an
   unknown kind and a missing or non-physical value rather than guessing
   a default that would hide a concern.
2. Normalise the threshold set: absolute potential limit, differential
   potential limit, deposition current density screening limit, bulk
   field safety factor and shield thickness guideline. A caller may
   override any of them; each override is validated the same way.
3. For an external-surface, compute the differential potential to the
   structure reference and, where an adjacent surface is given, to that
   neighbour. Raise a structure-referenced finding, an adjacent-surface
   finding and an absolute frame finding independently -- one item can
   carry all three.
4. For a buried-dielectric, compute the bulk field as deposited current
   density times resistivity, compare it against the dielectric strength
   divided by the safety factor, and separately compare the deposition
   rate against the screening limit. Add a marginal finding when the
   field sits inside the top tenth of the allowable band, and a shielding
   finding when the aluminium-equivalent thickness is below guideline.
5. For a floating-conductor, check the bonding record: not bonded is a
   critical finding, bonded through a resistance above the bonding limit
   is a major one.
6. Rank the item: severity is the worst finding it carries (watch, major,
   critical), and an item is only concern-free when its finding list is
   empty.
7. Roll the item list up: count findings by severity, list the items that
   are not concern-free, and report the worst severity on the design.

## Pitfalls

- Reading a large absolute frame potential as an imminent discharge --
  a uniformly charged structure with no differential across a dielectric
  boundary has nothing to break down; it is the differential that arcs.
- Substituting the deposition-rate screen for the bulk-field check, or
  the reverse -- a high-resistivity dielectric can fail the field check
  at a benign deposition rate, and a low-resistivity one can pass the
  field check while the rate is well above the screening limit.
- Applying the dielectric strength directly as the allowable -- the
  allowable is the strength reduced by the safety factor, and skipping
  the reduction silently removes the whole margin.
- Assuming a metallic item is grounded because it is metallic -- bonding
  is a recorded fact about the item, and an unrecorded bond is treated as
  a finding rather than as a pass.
- Deciding a boundary case on the raw floating-point ordering -- a
  difference of two potentials or a product of a current density and a
  resistivity can land just above a limit it physically meets, so the
  comparison carries a tolerance instead of the limit being relaxed.

## Behavior contract (gate 3)

The item normalisation, differential-potential computation, bulk-field
and deposition-rate checks, bonding checks, severity ranking and item-list
roll-up are exercised by the gate 3 contract test:
scripts/test_e2006_common_charging_engineering_concerns.py against
scripts/e2006_common_charging_engineering_concerns_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_common_charging_engineering_concerns.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
