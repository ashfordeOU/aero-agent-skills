---
name: e2007-static-charging-verification
description: "Assess the static-charging control provisions of a vehicle. Use when ECSS-E-ST-20-07C clause 5.3.5 calls for examination of the materials, bonding straps and blankets fitted for potential equalization: place each surface material in its conductive, dissipative or insulating resistivity band, refuse an insulating exposed surface, derive each bonding strap DC resistance from its geometry and compare it with the ceiling of its bonding category, compute the charge relaxation time from volume resistivity and permittivity, and size every blanket ground-tab count against blanket area with a redundancy floor. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, static-charging-verification, potential-equalization-bonding, bonding-strap-dc-resistance, thermal-blanket-ground-tabs, surface-sheet-resistivity-band, static-charge-relaxation-time."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-static-charging-verification, potential-equalization-bonding, bonding-strap-dc-resistance, thermal-blanket-ground-tabs, surface-sheet-resistivity-band, static-charge-relaxation-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Static Charging Verification (space-systems/ecss/e2007-static-charging-verification)

Use when the task is the static-charging verification of
ECSS-E-ST-20-07C clause 5.3.5 — examining the materials, the bonding
straps and the thermal blankets a vehicle carries for potential
equalization, and deciding whether they actually hold every exposed
surface at the same potential.

## Domain quick reference

- The provisions are verified as three populations, and none of them
  covers for another. Surface materials decide whether charge can build
  up at all; bonding straps decide whether a fitting that does charge
  can bleed off; blankets decide whether the largest exposed dielectric
  area on the vehicle is tied to structure. A vehicle can pass on two
  populations and still charge.
- A surface material is placed by its sheet resistivity into a
  conductive, a static-dissipative or an insulating band. Only the first
  two are acceptable on an exposed surface: an insulating exposed
  surface stores charge and eventually equalizes through an arc rather
  than through the bonding provisions. The two band edges are round
  decades, so a material specified exactly at a decade is compared with
  a relative tolerance and is not pushed into the worse band by the
  representation of that decade.
- A bonding strap is verified against the ceiling of its own bonding
  category, not against a single number. The static-equalization
  category is the loosest, because bleeding off charge needs only a
  resistive path; an RF-reference strap is orders of magnitude tighter,
  and a shock-hazard or lightning-current path sits between them. Using
  the loosest ceiling everywhere passes straps that were never meant to
  carry that function.
- Where the strap is not measured it is computed from material and
  geometry: resistivity times length over cross-section. A strap sized
  exactly to its ceiling can land a unit in the last place above it once
  those three numbers are multiplied, so the ceiling comparison carries
  a relative tolerance and the ceiling itself is never relaxed.
- A blanket is grounded by layer and by tab. Every conductive layer is
  tied, not only the outermost, and the number of ground tabs follows
  the blanket area against a maximum area per tab, with a floor of two
  so that a single broken tab does not float the blanket. A blanket
  whose area is an exact multiple of the area per tab must not acquire a
  spurious extra tab from the representation of that division.
- Charge relaxation is the time answer to the same question: the time
  constant of a dielectric surface is its volume resistivity times its
  absolute permittivity, and a surface slower than the declared
  equalization limit is a finding even when its band is acceptable.

## Workflow

1. Normalize the equalization limit and the maximum area per ground tab;
   a non-positive value for either is an input error.
2. For each surface material, place the sheet resistivity in its band
   and record whether the surface is exposed. An insulating exposed
   surface is a finding; a buried one is not.
3. Compute the charge relaxation time from the volume resistivity and
   the relative permittivity, and compare it with the equalization limit
   under an explicit tolerance. Refuse a relative permittivity below
   unity rather than clamping it.
4. For each bonding strap, resolve its bonding category, take its
   measured resistance or compute it from resistivity, length and
   cross-section, and compare it with that category's ceiling.
5. For each blanket, check that every layer is grounded and that the
   declared tab count reaches the count its area requires, taking the
   rounding up on a value nudged down so an exact multiple is not
   inflated.
6. Collect one named finding per defect — insulating exposed surface,
   slow relaxation, strap over its ceiling, ungrounded layer,
   insufficient tabs — and keep the per-item reports alongside them.
7. Report the three populations and the finding list; the provisions are
   acceptable only when that list is empty.

## Pitfalls

- Verifying bonding straps alone and calling static charging closed. A
  perfectly bonded fitting on an insulating painted skin does nothing
  for the skin, which is the largest charging area on the vehicle.
- Applying one resistance ceiling to every strap. The ceiling belongs to
  the bonding category, and a strap that comfortably meets the
  static-equalization figure can be two orders of magnitude outside an
  RF-reference requirement.
- Grounding the outer blanket layer only. Inner layers charge through
  the same environment and discharge to whatever is nearest, so a
  partially grounded blanket is an ungrounded blanket for this clause.
- Rounding the ground-tab count with a bare ceiling on a float division.
  A blanket area that is an exact multiple of the area per tab divides
  to a value a unit in the last place above the integer on one platform
  and below it on another, which silently adds a tab. Nudge the value
  down by a named amount before rounding up.
- Judging a decade-specified material with a strict inequality against
  the decade. The decade is not exactly representable, so a material
  written to sit on the band edge can fall into the worse band on one
  platform only. Compare the edges with a relative tolerance.

## Behavior contract (gate 3)

The bonding-category resolution, strap-resistance computation and
ceiling comparison, surface-resistivity banding, charge-relaxation
timing, blanket layer and ground-tab checks and the three-population
verdict are exercised by the gate 3 contract test:
`scripts/test_e2007_static_charging_verification.py` against
`scripts/e2007_static_charging_verification_logic.py` (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_static_charging_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
